"""Chapter 11 spike 1: how long can a kept-open connection to each external service sit idle before the
next request pays the set-up cost again? Decides the interval of the keep-alive of alternative C.

    python docs/ch11/spike/measure_idle.py            (about 15 minutes; both services in parallel)

For each service and each idle time: empty the connection pool, make a call (cold: new connection), wait the idle
time, make the call again on the pooled connection. The second time is the one that matters: if the server closed
the idle connection, `_http_json` retries once on a new connection and the time shows the set-up cost.
No quota is used: the Open-Meteo call is the product's own current-weather query (free, no key) and the routing
service is asked only for its root path, which costs no quota (route_adapter.warm_up does the same).
Writes docs/ch11/data/idle_sensitivity.csv. (The committed file is the log of the first full pass and the start of the second: the run was stopped after 14 of 24 trials to free the network for the dispatch runs.)
"""
import csv
import os
import sys
import threading
import time
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from src.c3_data_adapter import route_adapter as ra  # noqa: E402

IDLE = [5, 15, 30, 60, 120, 240]
REPS = 2
OUT = os.path.join(ROOT, "docs", "ch11", "data", "idle_sensitivity.csv")
rows, lock = [], threading.Lock()


def open_meteo_url():
    q = urllib.parse.urlencode({"latitude": 42.4491, "longitude": -76.4835,
                                "current": "temperature_2m,precipitation,wind_speed_10m", "timezone": "auto"})
    return "https://api.open-meteo.com/v1/forecast?" + q


def call(url):
    s = time.perf_counter()
    try:
        ra._http_json(url, timeout=10)
        ok = "ok"
    except Exception as e:  # a 404 on the routing root still leaves the connection open and is not a failure here
        ok = type(e).__name__
    return (time.perf_counter() - s) * 1000, ok


def worker(name, url):
    for rep in range(REPS):
        for idle in IDLE:
            with ra._pool_lock:
                for conns in ra._idle.values():
                    for c in conns:
                        c.close()
                ra._idle.clear()
            cold_ms, ok1 = call(url)
            time.sleep(idle)
            second_ms, ok2 = call(url)
            with lock:
                rows.append({"service": name, "rep": rep + 1, "idle_s": idle, "cold_ms": round(cold_ms),
                             "after_idle_ms": round(second_ms), "status_cold": ok1, "status_after": ok2})
                print(rows[-1], flush=True)


if __name__ == "__main__":
    ors = ra.ORS_BASE + "/"
    threads = [threading.Thread(target=worker, args=("open-meteo", open_meteo_url())),
               threading.Thread(target=worker, args=("openrouteservice-root", ors))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["service"], r["rep"], r["idle_s"])))
    print("wrote", OUT)
