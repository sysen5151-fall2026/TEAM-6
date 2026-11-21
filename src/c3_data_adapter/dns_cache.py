"""In-process name cache for the two external hosts (ADR 0012, alternative D).

Chapter 11 measured where the "cold connection" of Chapter 10 loses its seconds: on the development laptop, resolving a
host name took about 3.07 s (sometimes 1.07 s) on every new connection, while the TCP connect took 20 to 120 ms and the
TLS handshake 25 to 220 ms (docs/ch11/data/connection_phases.csv). A kept-open connection avoids the lookup; a cache of the
host's addresses avoids it for every new connection, and costs the services nothing.

`resolve(host)` returns an address from the cache (stale-while-revalidate: an entry older than REFRESH_S is served and
refreshed on a background thread, an entry older than MAX_AGE_S is not served). The first lookup of a host is a normal blocking
lookup, so start-up calls `prefetch` for the known hosts. The connection still verifies the certificate against the host
name (see `route_adapter._CachedHTTPSConnection`), so a cached address cannot change who is trusted. A failed connect
to a cached address drops the entry and the caller falls back to an ordinary lookup.
"""
import socket
import threading
import time

REFRESH_S = 60.0
MAX_AGE_S = 600.0
HOSTS = ("api.open-meteo.com", "api.openrouteservice.org")
STATS = {"hits": 0, "misses": 0, "refreshes": 0, "refresh_failures": 0}

_lock = threading.Lock()
_entries = {}     # host -> (address, resolved_at)
_refreshing = set()
_clock = time.monotonic


def _lookup(host: str, port: int = 443) -> str:
    return socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)[0][4][0]


def _refresh(host: str) -> None:
    try:
        address = _lookup(host)
        with _lock:
            _entries[host] = (address, _clock())
        STATS["refreshes"] += 1
    except OSError:
        STATS["refresh_failures"] += 1  # the old entry stays until it is too old to serve
    finally:
        with _lock:
            _refreshing.discard(host)


def resolve(host: str, port: int = 443) -> str:
    """An address for the host. Raises OSError only when there is no usable entry and a lookup fails."""
    now = _clock()
    with _lock:
        entry = _entries.get(host)
        start = False
        if entry is not None and REFRESH_S <= now - entry[1] < MAX_AGE_S and host not in _refreshing:
            _refreshing.add(host)
            start = True
    if start:
        threading.Thread(target=_refresh, args=(host,), name="dns-refresh", daemon=True).start()
    if entry is not None and now - entry[1] < MAX_AGE_S:
        STATS["hits"] += 1
        return entry[0]
    STATS["misses"] += 1
    address = _lookup(host, port)
    with _lock:
        _entries[host] = (address, _clock())
    return address


def forget(host: str) -> None:
    with _lock:
        _entries.pop(host, None)


def prefetch(hosts=HOSTS) -> threading.Thread:
    """Resolve the known hosts on a background thread (start-up), so no commuter's request pays the first lookup."""
    def run():
        for host in hosts:
            try:
                resolve(host)
            except OSError:
                pass
    thread = threading.Thread(target=run, name="dns-prefetch", daemon=True)
    thread.start()
    return thread
