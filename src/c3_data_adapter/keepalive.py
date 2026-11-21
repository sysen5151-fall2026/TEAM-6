"""Keep the connections to the two external services open between commuters (ADR 0012, Chapter 10 decision D6).

The first request after a quiet period pays the connection set-up, which the Chapter 10 measurements put at 1.1 to 3.6 s
and which alone breaks the 3-second display time (requirement 3.4.2.1). A light request every INTERVAL_S keeps one
connection to each service open in the shared pool of `route_adapter._http_json`, so the commuter's request finds it warm.

What is sent: Open-Meteo gets the same current-weather query as a plan, for a fixed point on campus (no user data);
the routing service gets its root path, which costs no quota (the same request `warm_up` makes), three at once. At the default
interval that is 1,440 Open-Meteo calls a day against the free plan's 10,000 (https://open-meteo.com/en/terms).
Failures are ignored on purpose: a keep-alive that fails must never reach a commuter.
"""
import os
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from src.c3_data_adapter import route_adapter

INTERVAL_S = float(os.environ.get("ECOCOMMUTE_KEEPALIVE_S", "60"))
CAMPUS = (42.4491, -76.4835)  # Cornell Arts Quad, the same coarse point the sample places use
TIMEOUT_S = 5.0
STATS = {"ticks": 0, "failures": 0}

_thread = None
_stop = threading.Event()


def _targets() -> list:
    """(url, connections to keep open). A plan asks the routing service three times at once (drive, walk, bike), so three
    connections are kept open to it; the weather service is asked once."""
    query = urllib.parse.urlencode({"latitude": CAMPUS[0], "longitude": CAMPUS[1],
                                    "current": "temperature_2m,precipitation,wind_speed_10m", "timezone": "auto"})
    urls = [("https://api.open-meteo.com/v1/forecast?" + query, 1)]
    if route_adapter._api_key():
        urls.append((route_adapter.ORS_BASE + "/", len(route_adapter.PROFILES)))
    return urls


def _ask(url: str) -> None:
    try:
        route_adapter._http_json(url, timeout=TIMEOUT_S)
    except Exception:  # a 404 or a page that is not JSON still leaves the connection open; a real failure is only counted
        if "open-meteo" in url:
            STATS["failures"] += 1


def tick() -> None:
    """One round of light requests: for each service as many at once as a plan makes, so that many connections stay open.
    Never raises."""
    STATS["ticks"] += 1
    jobs = [url for url, n in _targets() for _ in range(n)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        list(pool.map(_ask, jobs))


def _loop(interval_s: float) -> None:
    tick()
    while not _stop.wait(interval_s):
        tick()


def start(interval_s: float = None) -> bool:
    """Start the background thread once; returns False when it is already running."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return False
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(interval_s or INTERVAL_S,), name="keepalive", daemon=True)
    _thread.start()
    return True


def stop() -> None:
    _stop.set()
