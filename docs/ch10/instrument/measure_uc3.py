"""Instrumentation harness for the Chapter 10 measured-behavior comparison.

    python docs/ch10/instrument/measure_uc3.py [runs] [pause_seconds] [warm|cold] [live|off]

Runs the scenario that SC.1 simulates (open the planner, submit a start and a destination, choose a way,
see the result) against the REAL web application (Flask app of src/c1_web_front_end, real SQLite account
database in a temporary folder, real OpenRouteService and Open-Meteo calls). Nothing in the product source is
changed: the harness wraps the functions that sit on the boundary of each participant of the sequence
diagram and stamps entry and exit (time.perf_counter_ns) of every call.

What is real: every layer from the Flask request handler down to the HTTPS calls to the two external services.
What is not: the browser (the Flask test client is in-process, so no network time between a browser and the
server and no page rendering in a browser) and the Commuter (zero think time; human actions of SC.1 are not
measured here).

Each run uses a different start/destination pair from the eight sample places, so no run is answered from
the route cache, and the in-process route cache is cleared before each run. The pause between runs keeps the
OpenRouteService free plan under its per-minute limit (3 directions requests per run). The API key is read
from the environment by the product itself and is never printed or written.

Two conditions. warm: the connections to the two services stay open between runs, as the product keeps them
(route_adapter._http_json). cold: every kept-open connection is closed before each run, which is what happens
when commuters are minutes apart and the services have closed the idle connections.

Writes docs/ch10/data/measured_spans_<mode>.csv (every boundary call with entry and exit stamps),
measured_runs_<mode>.csv (per-run stage durations) and measured_meta_<mode>.json.
"""
import csv
import importlib
import importlib.metadata
import itertools
import json
import os
import platform
import sys
import threading
import time
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(HERE, "..", "data")
sys.path.insert(0, ROOT)

from tests.webhelper import make_client  # noqa: E402  (the test helper builds a signed-in client on a temporary database)

route_adapter = importlib.import_module("src.c3_data_adapter.route_adapter")
weather_adapter = importlib.import_module("src.c3_data_adapter.weather_adapter")
comparison = importlib.import_module("src.c2_application_service.comparison")
plan_mod = importlib.import_module("src.c2_application_service.plan")
confirmation = importlib.import_module("src.c2_application_service.confirmation")
web_app = importlib.import_module("src.c1_web_front_end.web_app")


class Recorder:
    def __init__(self):
        self.lock = threading.Lock()
        self.spans = []     # (phase, boundary, enter_ns, exit_ns, thread)
        self.phase = ""

    def add(self, boundary, t0, t1):
        with self.lock:
            self.spans.append((self.phase, boundary, t0, t1, threading.get_ident()))


REC = Recorder()


def wrap(module, name, boundary, key=None):
    orig = getattr(module, name)

    def inner(*a, **k):
        b = key(*a, **k) if key else boundary
        t0 = time.perf_counter_ns()
        try:
            return orig(*a, **k)
        finally:
            REC.add(b, t0, time.perf_counter_ns())

    inner.__wrapped__ = orig
    setattr(module, name, inner)


def instrument():
    wrap(web_app, "plan_commute", "plan_commute@web")                # C.0.1 -> C.0.2 boundary: validated entry handed on
    wrap(confirmation, "plan_commute", "plan_commute@confirm")       # the re-plan inside "choose a way"
    wrap(comparison, "geocode", "geocode")
    wrap(comparison, "get_route_options", "get_route_options")       # C.0.2 request routes (dispatch + wait)
    wrap(comparison, "select_emission_factor", "select_factor")      # C.0.2.2
    wrap(plan_mod, "compare_modes", "compare_modes")                     # C.0.3 estimation incl. the calls above
    wrap(plan_mod, "find_bus", "find_bus")                           # bus planner (not in SC.1)
    wrap(plan_mod, "current_weather", "current_weather")             # C.0.2.3 request weather (incl. X.3)
    wrap(plan_mod, "resolve_trip_forecast", "resolve_forecast")     # C.0.2.4
    wrap(plan_mod, "recommend_mode", "recommend_mode")               # C.0.5
    wrap(confirmation, "add_confirmed", "add_confirmed")             # C.0.4 insert
    wrap(web_app, "confirm_trip", "confirm_trip")                    # C.0.4 record trip and update progress
    wrap(web_app, "render_template", None, key=lambda name, **k: "render:" + name)   # C.0.6 / C.0.1 page render

    # external boundaries: the HTTPS call itself
    orig_ors = route_adapter._http_json

    def ors_call(url, *a, **k):
        t0 = time.perf_counter_ns()
        try:
            return orig_ors(url, *a, **k)
        finally:
            REC.add("X.6 call", t0, time.perf_counter_ns())

    route_adapter._http_json = ors_call
    orig_wx = weather_adapter._http_json

    def wx_call(url, *a, **k):
        t0 = time.perf_counter_ns()
        try:
            return orig_wx(url, *a, **k)
        finally:
            REC.add("X.3 call", t0, time.perf_counter_ns())

    weather_adapter._http_json = wx_call


def _haversine_m(a, b):
    import math
    (la1, lo1), (la2, lo2) = route_adapter.SAMPLE_PLACES[a], route_adapter.SAMPLE_PLACES[b]
    p1, p2, dl = math.radians(la1), math.radians(la2), math.radians(lo2 - lo1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def pairs(n):
    names = list(route_adapter.SAMPLE_PLACES)
    # Gates Hall and Duffield Hall are 43 m apart; OpenRouteService routes the walk as 0.01 km, which the product refuses as "same place"
    # (MIN_DISTANCE_KM = 0.05), so the pair (in both directions) is left out
    allp = [(a, b) for a in names for b in names if a != b and _haversine_m(a, b) >= 100]
    # spread: take every 9th pair (9 and 56 share no factor, so all 56 pairs are visited once) so consecutive runs do not share the start place
    import math
    step = next(k for k in range(7, 100) if math.gcd(k, len(allp)) == 1)   # coprime with the number of pairs, so every pair is visited once
    order = [allp[(i * step) % len(allp)] for i in range(len(allp))]
    seen, out = set(), []
    for p in order:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:n]


def total(spans, boundary, thread=None):
    return sum((s[3] - s[2]) for s in spans if s[1] == boundary and (thread is None or s[4] == thread)) / 1e9


def one(spans, boundary, default=0.0):
    xs = [s for s in spans if s[1] == boundary]
    return (xs[0][3] - xs[0][2]) / 1e9 if xs else default


def derive(run_spans, t_post0, t_post1, t_get_open, t_conf0, t_conf1, t_done1, ors_ok):
    """Per-run stage durations in seconds from the stamped spans."""
    sp = [s for s in run_spans if s[0] == "plan"]
    ch = [s for s in run_spans if s[0] == "choose"]
    pc = [s for s in sp if s[1] == "plan_commute@web"][0]
    ors = [s for s in sp if s[1] == "X.6 call"]
    wx = [s for s in sp if s[1] == "X.3 call"]
    gro = [s for s in sp if s[1] == "get_route_options"][0]
    cm = [s for s in sp if s[1] == "compare_modes"][0]
    resolve = [s for s in sp if s[1] == "resolve_forecast"][0]
    cw = [s for s in sp if s[1] == "current_weather"][0]
    x6 = (max(s[3] for s in ors) - min(s[2] for s in ors)) / 1e9 if ors else 0.0
    x3 = (wx[0][3] - wx[0][2]) / 1e9 if wx else 0.0
    factor_sum = total(sp, "select_factor")
    geo = total(sp, "geocode")
    gro_t = (gro[3] - gro[2]) / 1e9
    cm_t = (cm[3] - cm[2]) / 1e9
    out = {
        "open_total": t_get_open,                                           # Present Entry Form (GET /)
        "validate": (pc[2] - t_post0) / 1e9,                                # C.0.1 Validate Trip Entry (routing, session, token, form checks, saved vehicles)
        "request_routes": max(0.0, gro_t - x6),                             # C.0.2 Request Routes (pool dispatch and join)
        "route_service": x6,                                                # X.6 Return Routes (slowest of the parallel calls, wall span)
        "geocode": geo,                                                     # not a separate action of SC.1 (sample places, local)
        "select_factors": factor_sum,                                       # C.0.2 Select Emission Factors
        "estimate": max(0.0, cm_t - geo - gro_t - factor_sum),              # C.0.3 Estimate Mode Emissions
        "find_bus": total(sp, "find_bus"),                                  # not modeled in SC.1
        "request_weather": max(0.0, (cw[3] - cw[2]) / 1e9 - x3),            # C.0.2 Request Weather (overhead around the call)
        "weather_service": x3,                                              # X.3 Return Weather Forecast
        "resolve": (resolve[3] - resolve[2]) / 1e9,                         # C.0.2 Resolve Trip Forecast
        "recommend": total(sp, "recommend_mode"),                           # C.0.5 Recommend Feasible Mode
        "present": total(sp, "render:plan.html"),                           # C.0.6 Present Comparison (template render)
        "plan_total": (t_post1 - t_post0) / 1e9,                            # response time R1: submit to page returned
        "refdata": (resolve[3] - pc[2]) / 1e9,                              # validated entry to trip forecast returned (requirement 5.5.3)
    }
    # choose a way
    cpc = [s for s in ch if s[1] == "plan_commute@confirm"]
    ct = [s for s in ch if s[1] == "confirm_trip"]
    out["record"] = ((ct[0][3] - ct[0][2]) - (cpc[0][3] - cpc[0][2])) / 1e9 if ct and cpc else 0.0   # C.0.4 Record Trip and Update Progress (without the re-plan)
    out["replan"] = (cpc[0][3] - cpc[0][2]) / 1e9 if cpc else 0.0       # not modeled in SC.1: the whole comparison is computed again
    out["replan_weather_call"] = total(ch, "X.3 call")
    out["add_confirmed"] = total(ch, "add_confirmed")
    out["display"] = total([s for s in ch if s[0] == "choose"], "render:done.html")
    out["result_total"] = (t_done1 - t_conf0) / 1e9                         # response time R2: choice submitted to result page returned
    out["ors_ok"] = int(ors_ok)
    return out


def drop_idle_connections():
    """Close every kept-open connection, as if the servers had closed them while the app sat idle between two commuters."""
    with route_adapter._pool_lock:
        for conns in route_adapter._idle.values():
            for c in conns:
                c.close()
        route_adapter._idle.clear()


def main(runs=40, pause=8.0, mode="warm", ors="live"):
    if ors == "off":
        os.environ["ORS_API_KEY"] = ""   # the documented offline configuration: routes are the labelled straight-line estimate; Open-Meteo is still live
    instrument()
    suffix = "_nors" if ors == "off" else ""
    client = make_client("measure")
    plist = pairs(runs)
    runs = len(plist)
    today = date.today().isoformat()
    rows, all_spans = [], []
    fails = 0
    ors_active = route_adapter.place_search_is_live()
    print(f"runs={runs} mode={mode} ors_key_present={ors_active} pause={pause}s")
    for i, (a, b) in enumerate(plist, 1):
        if ors != "off" and route_adapter._paused("route"):   # a 403/429 answer pauses routing for 60 s: stop instead of spending more quota
            print(f"run {i:2d}: routing is paused after a refusal (quota or rate limit); campaign stopped with {len(rows)} runs", flush=True)
            break
        route_adapter._route_cache.clear()
        if mode == "cold":
            drop_idle_connections()
        REC.spans = []
        # 1. open the planner
        REC.phase = "open"
        t0 = time.perf_counter_ns()
        r = client.get("/")
        t_open = (time.perf_counter_ns() - t0) / 1e9
        assert r.status_code == 200
        # 2. submit start and destination
        REC.phase = "plan"
        t_post0 = time.perf_counter_ns()
        r = client.post("/", data={"origin": a, "destination": b, "when": ""})
        t_post1 = time.perf_counter_ns()
        assert r.status_code == 200, r.status_code
        ors_ok = len(route_adapter._route_cache) > 0   # a plan is cached only when all three routes came from OpenRouteService
        # 3. choose a way and see the result
        REC.phase = "choose"
        t_c0 = time.perf_counter_ns()
        r = client.post("/confirm", data={"origin": a, "destination": b, "mode": "walk", "date": today, "when": ""})
        if r.status_code not in (302, 303):
            print(f"run {i:2d} SKIPPED: choose returned status {r.status_code}", flush=True)
            continue
        loc = r.headers["Location"]
        t_c1 = time.perf_counter_ns()
        REC.phase = "done"
        r2 = client.get(loc)
        t_done = time.perf_counter_ns()
        assert r2.status_code == 200
        spans = list(REC.spans)
        # render of done page belongs to the choose phase
        spans = [("choose" if s[0] == "done" else s[0],) + s[1:] for s in spans]
        row = derive(spans, t_post0, t_post1, t_open, t_c0, t_c1, t_done, ors_ok)
        row["run"] = i
        row["pair"] = f"{a} > {b}"
        rows.append(row)
        base = t_post0
        for s in spans:
            all_spans.append((i, s[0], s[1], (s[2] - base) / 1e9, (s[3] - base) / 1e9, s[4]))
        print(f"run {i:2d} plan {row['plan_total']:.3f}s  X.6 {row['route_service']:.3f}  X.3 {row['weather_service']:.3f}  result {row['result_total']:.3f}  ors_ok={row['ors_ok']}", flush=True)
        fails = fails + 1 if (ors != "off" and not ors_ok) else 0
        if fails >= 2:
            print(f"runs {i - 1} and {i}: routes not answered by OpenRouteService; campaign stopped with {len(rows)} runs", flush=True)
            break
        if i < runs:
            time.sleep(pause)
    os.makedirs(DATA, exist_ok=True)
    cols = ["run", "pair", "ors_ok", "open_total", "validate", "request_routes", "route_service", "geocode", "select_factors", "estimate", "find_bus",
            "request_weather", "weather_service", "resolve", "recommend", "present", "plan_total", "refdata", "record", "replan", "replan_weather_call",
            "add_confirmed", "display", "result_total"]
    with open(os.path.join(DATA, f"measured_runs_{mode}{suffix}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] if isinstance(r[c], (int, str)) else f"{r[c]:.6f}" for c in cols])
    with open(os.path.join(DATA, f"measured_spans_{mode}{suffix}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "phase", "boundary", "enter_s", "exit_s", "thread"])
        for s in all_spans:
            w.writerow([s[0], s[1], s[2], f"{s[3]:.6f}", f"{s[4]:.6f}", s[5]])
    meta = {
        "date": today, "runs": runs, "pause_s": pause, "python": platform.python_version(), "platform": platform.platform(),
        "flask": importlib.metadata.version("flask"), "mode": mode, "ors": ors,
        "ors_key_present": ors_active, "weather_timeout_s": 1.0,
        "tcat_index_present": os.path.exists(os.path.join(ROOT, "data", "tcat", "tcat.sqlite")),
        "client": "Flask in-process test client (no browser, no network between browser and server)",
    }
    with open(os.path.join(DATA, f"measured_meta_{mode}{suffix}.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("done", meta)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    p = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    m = sys.argv[3] if len(sys.argv) > 3 else "warm"
    o = sys.argv[4] if len(sys.argv) > 4 else "live"
    main(n, p, m, o)
