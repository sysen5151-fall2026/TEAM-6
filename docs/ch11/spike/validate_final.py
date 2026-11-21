"""Chapter 11 validation: the product as built after the change against the product as it was, live, connections closed.

    python docs/ch11/spike/validate_final.py 10 10        (runs per side, seconds between runs; needs ORS_API_KEY)

asbuilt  plan.DISPATCH = sequential, no deadlines, no name cache: the Chapter 10 product.
final    the defaults of the repository: concurrent dispatch, name cache (filled once, as at server start-up), weather deadline
         1.0 s, route deadline 1.2 s with the labelled fallback.
Before every run the harness closes every kept-open connection (Chapter 10's cold condition); the name cache is not emptied, because
the server keeps it. The two sides alternate so that network drift falls on both. Directions requests are live: 3 per run (drive, walk, bike; the plan shows drive and walk), paced
so as to stay under the published 40 a minute. Writes docs/ch11/data/final_validation.csv and .json.
"""
import csv
import itertools
import json
import os
import statistics
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from src.c2_application_service import plan as plan_module  # noqa: E402
from src.c3_data_adapter import dns_cache, route_adapter  # noqa: E402

DEFAULTS = dict(DISPATCH=plan_module.DISPATCH, WEATHER_DEADLINE_S=plan_module.WEATHER_DEADLINE_S,
                ROUTE_DEADLINE_S=route_adapter.ROUTE_DEADLINE_S, USE_DNS_CACHE=route_adapter.USE_DNS_CACHE)
PLACES = list(route_adapter.SAMPLE_PLACES)
PAIRS = [(a, b) for a, b in itertools.permutations(PLACES, 2)
         if route_adapter._haversine_km(route_adapter.geocode(a), route_adapter.geocode(b)) > 0.3]


def configure(side):
    if side == "asbuilt":
        plan_module.DISPATCH, plan_module.WEATHER_DEADLINE_S = "sequential", 60.0
        route_adapter.ROUTE_DEADLINE_S, route_adapter.USE_DNS_CACHE = 60.0, False
    else:
        plan_module.DISPATCH, plan_module.WEATHER_DEADLINE_S = DEFAULTS["DISPATCH"], DEFAULTS["WEATHER_DEADLINE_S"]
        route_adapter.ROUTE_DEADLINE_S, route_adapter.USE_DNS_CACHE = DEFAULTS["ROUTE_DEADLINE_S"], DEFAULTS["USE_DNS_CACHE"]


def drop_connections():
    with route_adapter._pool_lock:
        for conns in route_adapter._idle.values():
            for c in conns:
                c.close()
        route_adapter._idle.clear()


def one(side, pair, run):
    configure(side)
    route_adapter._route_cache.clear()
    drop_connections()
    s = time.perf_counter()
    result = plan_module.plan_commute(*pair)
    elapsed = time.perf_counter() - s
    # the plan shows drive and walk (a bike or scooter only when the commuter has one), so two rows can be routed
    routed = sum(1 for c in result.comparisons if c.mode in ("drive", "walk") and c.source == "OpenRouteService")
    return {"side": side, "run": run, "pair": " > ".join(pair), "plan_s": round(elapsed, 4), "routed_modes": routed,
            "weather_applied": int(result.recommendation.weather_note.startswith("Weather at"))}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    pause = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    configure("final")
    dns_cache.prefetch().join()
    configure("asbuilt")
    one("asbuilt", PAIRS[0], 0)   # an untimed first request for the as-built side (process start-up)
    rows = []
    for i in range(n):
        for side in (("asbuilt", "final") if i % 2 == 0 else ("final", "asbuilt")):
            if route_adapter._paused("route"):
                print("routing paused after a refusal: stopped", flush=True)
                break
            time.sleep(pause)
            row = one(side, PAIRS[(len(rows) * 5 + 2) % len(PAIRS)], i + 1)
            rows.append(row)
            print(row, flush=True)
    summary = {}
    for side in ("asbuilt", "final"):
        xs = [r["plan_s"] for r in rows if r["side"] == side]
        sub = [r for r in rows if r["side"] == side]
        summary[side] = {"n": len(xs), "median": statistics.median(xs), "mean": statistics.mean(xs), "max": max(xs),
                         "within_3s": sum(x <= 3 for x in xs) / len(xs),
                         "all_routes_live": sum(1 for r in sub if r["routed_modes"] == 2),
                         "weather_applied": sum(r["weather_applied"] for r in sub)}
    data = os.path.join(ROOT, "docs", "ch11", "data")
    with open(os.path.join(data, "final_validation.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(data, "final_validation.json"), "w", encoding="utf-8") as f:
        json.dump({"stamp": time.strftime("%Y-%m-%d %H:%M:%S"), "summary": summary}, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
