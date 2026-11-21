"""Chapter 11 spike 2: the real plan path under alternatives A, B, C and D, against the live services.

    python docs/ch11/spike/measure_dispatch.py warm 8            # A and B interleaved, connections kept open (3 s apart)
    python docs/ch11/spike/measure_dispatch.py gap A 8 120       # alternative A alone, 120 s between requests
    python docs/ch11/spike/measure_dispatch.py gap B 8 120
    python docs/ch11/spike/measure_dispatch.py gap C 8 123 20    # C: concurrent dispatch plus a keep-alive every 20 s
    python docs/ch11/spike/measure_dispatch.py gap D 8 120       # D: concurrent dispatch plus the name cache (dns_cache.py)

A  sequential dispatch (src/c2_application_service/plan.py DISPATCH="sequential", the Chapter 10 build)
B  concurrent dispatch (DISPATCH="concurrent")
C  concurrent dispatch plus the keep-alive of src/c3_data_adapter/keepalive.py
D  concurrent dispatch plus the name cache of src/c3_data_adapter/dns_cache.py (found by spike 1b, connection_phases.csv)
(E, queued handling, is not run: it is replayed on the B measurements, see docs/ch11/sim/model.py)
In the gap condition each alternative runs in its own process, so that one alternative cannot leave open connections for another
(an interleaved first attempt showed B inheriting A's connections). One untimed request is made first (what the server does
at start-up); after it the timed requests are `gap` seconds apart and the connections are not closed by the harness: whatever
the services and the network do with an idle connection is what is measured. The four processes were run side by side.
The deadlines of Chapter 12 are switched off here (WEATHER_DEADLINE_S, ROUTE_DEADLINE_S set high) so that each alternative is
measured as designed; the deadlines are a guardrail, not a candidate. The harness calls plan_commute directly (no web
server, no browser), as Chapter 10 did through the test client, so times are the system side only.
Each run uses a different pair of the eight sample places and an empty route cache.
The routing service refused requests during the first campaign (the warm one stopped after 14 runs, `dispatch_warm.csv`; most
likely the published limit of 40 directions requests a minute, since the runs were 3 s apart). For the gap condition the
directions call is therefore replaced (set PROXY_ROUTES=1) by a request to the root path of the same host,
which costs no quota and meets the same connection set-up as a directions call; what it leaves out is the directions
computation itself (about 25 ms more than the root path when warm: 0.126 s against 0.101 s). The weather call is always the
real Open-Meteo call. The key is read from the environment by the product, never printed.
C is run with a gap of 123 s, not 120 s: a first run of C with 120 s (kept as dispatch_gap_C_phase_locked.csv) put every request
8 s after a keep-alive round (128 s after the start is 6 rounds plus 8 s), so it measured one idle age only. With 123 s the age
of the connection when the request arrives takes the values 8, 11, 14, 17, 0, 3, 6 and 9 s.
Writes docs/ch11/data/dispatch_<condition>[_<alternative>].csv and .json.
"""
import csv
import itertools
import json
import os
import statistics
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from src.c2_application_service import plan as plan_module  # noqa: E402
from src.c3_data_adapter import dns_cache, keepalive, route_adapter  # noqa: E402

DATA = os.path.join(ROOT, "docs", "ch11", "data")
PLACES = list(route_adapter.SAMPLE_PLACES)
PAIRS = [(a, b) for a, b in itertools.permutations(PLACES, 2)
         if route_adapter._haversine_km(route_adapter.geocode(a), route_adapter.geocode(b)) > 0.3]
spans = []
span_lock = threading.Lock()


def timed(fn, name):
    def wrapper(*args, **kwargs):
        s = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            with span_lock:
                spans.append((name, time.perf_counter() - s))
    return wrapper


plan_module.current_weather = timed(plan_module.current_weather, "weather")


def proxy_route(mode, origin, dest):
    """Stands in for _ors_route when the quota is gone: a no-quota request to the same host, then a fixed answer."""
    try:
        route_adapter._http_json(route_adapter.ORS_BASE + "/", timeout=10)
    except ValueError:
        pass  # the root path answers HTML; the connection is what is being measured
    return route_adapter.RouteOption(mode, 1.0, 5.0, "OpenRouteService", ((origin.lat, origin.lon), (dest.lat, dest.lon)))


if os.environ.get("PROXY_ROUTES") == "1":
    route_adapter._ors_route = proxy_route
route_adapter._ors_route = timed(route_adapter._ors_route, "route")


def configure(strategy):
    plan_module.DISPATCH = "sequential" if strategy == "A" else "concurrent"
    plan_module.WEATHER_DEADLINE_S = 60.0
    route_adapter.ROUTE_DEADLINE_S = 60.0
    route_adapter.USE_DNS_CACHE = strategy == "D"


def one(strategy, pair, run):
    configure(strategy)
    route_adapter._route_cache.clear()
    with span_lock:
        spans.clear()
    s = time.perf_counter()
    result = plan_module.plan_commute(*pair)
    elapsed = time.perf_counter() - s
    with span_lock:
        got = list(spans)
    live = all(c.source.startswith("OpenRouteService") for c in result.comparisons if c.mode in ("drive", "walk", "bike"))
    if os.environ.get("PROXY_ROUTES") == "1":
        live = True  # routes are the fixed proxy answer by design
    return {"strategy": strategy, "run": run, "pair": " > ".join(pair), "plan_s": round(elapsed, 4),
            "route_max_s": round(max([d for n, d in got if n == "route"] or [0]), 4),
            "weather_s": round(max([d for n, d in got if n == "weather"] or [0]), 4),
            "routes_live": int(live), "weather_applied": int(result.recommendation.weather_note.startswith("Weather at"))}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(rows):
    out = {}
    for strategy in sorted({r["strategy"] for r in rows}):
        xs = [r["plan_s"] for r in rows if r["strategy"] == strategy]
        out[strategy] = {"n": len(xs), "median": statistics.median(xs), "mean": statistics.mean(xs), "p95": pct(xs, 95),
                         "max": max(xs), "within_3s": sum(x <= 3 for x in xs) / len(xs),
                         "within_1_2s": sum(x <= 1.2 for x in xs) / len(xs),
                         "routes_live": sum(r["routes_live"] for r in rows if r["strategy"] == strategy),
                         "weather_applied": sum(r["weather_applied"] for r in rows if r["strategy"] == strategy)}
    return out


def main():
    cond = sys.argv[1]
    if cond == "warm":
        strategies, n = ["A", "B"], int(sys.argv[2])
        gap = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
        interval, tag = 20.0, "warm"
    else:
        strategies, n = [sys.argv[2]], int(sys.argv[3])
        gap = float(sys.argv[4]) if len(sys.argv) > 4 else 120.0
        interval = float(sys.argv[5]) if len(sys.argv) > 5 else 20.0
        tag = f"gap_{strategies[0]}"
    s0 = strategies[0]
    configure(s0)
    if s0 == "C":
        keepalive.start(interval_s=interval)
    if s0 == "D":
        dns_cache.prefetch().join()           # what the server does at start-up
    if cond == "gap":
        one(s0, PAIRS[1], 0)                  # the untimed first request (process start-up cost is not an alternative's cost)
        if s0 == "C":
            time.sleep(interval + 8)
    rows, k = [], 0
    for i in range(n):
        order = strategies if i % 2 == 0 else strategies[::-1]   # alternate the order so neither always goes first
        for strategy in order:
            if route_adapter._paused("route"):
                print("routing paused after a refusal (quota or rate limit): stopped", flush=True)
                break
            time.sleep(gap)
            row = one(strategy, PAIRS[(k * 7 + 3) % len(PAIRS)], i + 1)
            k += 1
            row["condition"], row["gap_s"] = cond, gap
            rows.append(row)
            print(row, flush=True)
    keepalive.stop()
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, f"dispatch_{tag}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {"condition": cond, "gap_s": gap, "keepalive_s": interval if s0 == "C" else None,
               "stamp": time.strftime("%Y-%m-%d %H:%M:%S"), "summary": summarize(rows)}
    with open(os.path.join(DATA, f"dispatch_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
