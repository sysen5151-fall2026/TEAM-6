"""Place search and per-mode routes for C.3.

Uses OpenRouteService (ORS) when the ORS_API_KEY environment variable is set.
Without a key, or when a call fails, it falls back to a clearly labelled
estimate from sample places so the page keeps working.

Checked once against the live service on 2026-10-27 (geocode search and the
three Directions profiles on api.openrouteservice.org, free key). The unit
tests still use mocked responses; no automated test calls the network.
"""

import http.client
import io
import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from src.interfaces import Place, RouteOption
from src.model_trace import realizes

# ORS announced a move to api.heigit.org; the same paths returned 404 there on 2026-10-27,
# so the old host stays the default and ORS_BASE_URL can switch it without a code change.
ORS_BASE = os.environ.get("ORS_BASE_URL", "https://api.openrouteservice.org").rstrip("/")
TIMEOUT_S = 5
SUGGEST_TIMEOUT_S = 2.5  # a suggestion that takes longer is not worth waiting for
COOLDOWN_S = 60.0  # after a "quota exceeded" or "too many requests" answer, stop asking for this long
ONLINE_MIN_CHARS = 3  # sample places show from 2 characters; the online search starts at 3
LOCAL_RADIUS_KM = 40  # the service area: places are only searched within this distance of campus (Ithaca and its surroundings)

PROFILES = {"drive": "driving-car", "walk": "foot-walking", "bike": "cycling-regular"}
_route_pool = ThreadPoolExecutor(max_workers=len(PROFILES), thread_name_prefix="ors")  # long-lived, so its threads keep their connections

# Fallback assumptions (NOT measured): road distance = straight line x detour factor.
FALLBACK_DETOUR = {"drive": 1.3, "walk": 1.2, "bike": 1.25}
FALLBACK_SPEED_KMH = {"drive": 30.0, "walk": 5.0, "bike": 15.0}
FALLBACK_SOURCE = "estimate (straight line x detour factor), not a routed distance"

# Approximate coordinates (good to roughly 100 m), for the offline fallback only.
SAMPLE_PLACES = {
    "Cornell Arts Quad": (42.4491, -76.4835),
    "Collegetown": (42.4421, -76.4853),
    "Ithaca Commons": (42.4396, -76.4968),
    "Cornell Gates Hall": (42.4446, -76.4818),
    "Upson Hall": (42.4436, -76.4838),
    "Duffield Hall": (42.4445, -76.4823),
    "Olin Library": (42.4478, -76.4841),
    "Willard Straight Hall": (42.4466, -76.4857),
}

# Suggestions are biased towards the campus so "upson hall" finds Cornell's building first.
FOCUS_LON, FOCUS_LAT = -76.4835, 42.4491
MIN_SUGGEST_CHARS = 2
MAX_SUGGESTIONS = 5
_CACHE_LIMIT = 200
_place_cache = {}  # label.lower() -> Place, so a picked suggestion resolves to the same point
_suggest_cache = {}  # query.lower() -> tuple of Place, only successful ORS answers
_route_cache = {}  # (lat, lon, lat, lon) -> routes that all came from ORS
MAX_PATH_POINTS = 300
_backend = None  # a persistent cache (SqliteCache) when the application sets one


def set_cache_backend(backend) -> None:
    """Use `backend` to keep answers between runs (None to go back to memory only)."""
    global _backend
    _backend = backend


def _stored(namespace: str, key: str):
    return _backend.get(namespace, key) if _backend is not None else None


def _store(namespace: str, key: str, value) -> None:
    if _backend is not None:
        _backend.put(namespace, key, value)


def _place_to_dict(p: Place) -> dict:
    return {"label": p.label, "lat": p.lat, "lon": p.lon, "source": p.source}


def _place_from_dict(d: dict) -> Place:
    return Place(label=d["label"], lon=float(d["lon"]), lat=float(d["lat"]), source=d["source"])


def _places_from_payload(payload) -> tuple:
    try:
        return tuple(_place_from_dict(d) for d in payload["places"])
    except (KeyError, TypeError, ValueError):
        return None


def _route_to_dict(o) -> dict:
    return {"mode": o.mode, "distance_km": o.distance_km, "duration_min": o.duration_min, "source": o.source,
            "path": [list(p) for p in o.path]}


def _route_from_dict(d: dict):
    return RouteOption(d["mode"], float(d["distance_km"]), float(d["duration_min"]), d["source"],
                       tuple((float(a), float(b)) for a, b in d["path"]))


def _is_known(p: Place) -> bool:
    """A place that is not somebody's position: a sample place or one that was looked up by name."""
    if any(abs(lat - p.lat) < 0.0003 and abs(lon - p.lon) < 0.0003 for lat, lon in SAMPLE_PLACES.values()):
        return True
    return _backend is not None and _backend.known_place_near(p.lat, p.lon)


_paused_until = {"autocomplete": 0.0, "search": 0.0, "route": 0.0}  # separate quotas; monotonic time each is left alone until

# The page names the Commuter's own position like this; no search service is involved.
_MY_LOCATION = re.compile(r"^My location \((-?\d{1,3}\.\d+), (-?\d{1,3}\.\d+)\)$")


def sample_places() -> tuple:
    return tuple(SAMPLE_PLACES)


def _sample_matches(text: str) -> tuple:
    """Sample places whose name contains every word of the query."""
    words = text.lower().split()
    return tuple(
        Place(label=name, lon=lon, lat=lat, source="sample place list")
        for name, (lat, lon) in SAMPLE_PLACES.items()
        if all(w in name.lower() for w in words)
    )


def _remember(place: Place) -> None:
    if len(_place_cache) >= _CACHE_LIMIT:
        _place_cache.clear()
    _place_cache[place.label.lower()] = place
    _store("place", place.label.lower(), _place_to_dict(place))  # so a picked suggestion still resolves after a restart


def _quick_remote(text: str) -> tuple:
    """Online answers already known for this text, or for a shorter start of it, narrowed to this text."""
    key = text.lower()
    starts = [k for k in _suggest_cache if key.startswith(k)]
    if not starts:
        return ()
    words = key.split()
    return tuple(p for p in _suggest_cache[max(starts, key=len)] if all(w in p.label.lower() for w in words))


def _merge(samples, remote) -> tuple:
    """Sample matches first; a routed result for the same named place (within 0.5 km) replaces the sample."""
    found = [s for s in samples if not any(_same_place(s, r) for r in remote)] + list(remote)
    seen, unique = set(), []
    for place in found:
        if place.label.lower() not in seen:
            seen.add(place.label.lower())
            unique.append(place)
    chosen = tuple(unique[:MAX_SUGGESTIONS])
    for place in chosen:
        _remember(place)
    return chosen


def _geo_url(service: str, text: str, size: int) -> str:
    """A hard limit to the service area, so "statler" is not answered with Boston or Michigan."""
    params = {"api_key": _api_key(), "text": text, "size": size,
              "focus.point.lon": FOCUS_LON, "focus.point.lat": FOCUS_LAT,
              "boundary.circle.lon": FOCUS_LON, "boundary.circle.lat": FOCUS_LAT,
              "boundary.circle.radius": LOCAL_RADIUS_KM}
    return f"{ORS_BASE}/geocode/{service}?{urllib.parse.urlencode(params)}"


def _ask_remote(text: str):
    """Suggestions from the online service, or None when none could be had.

    Autocomplete is asked first. When its quota is used up the search service (a separate
    quota) answers instead, so suggestions keep coming; each is left alone for a minute
    after it says "quota exceeded". Only places within LOCAL_RADIUS_KM of campus are asked for.
    """
    for service in ("autocomplete", "search"):
        if _paused(service):
            continue
        try:
            data = _http_json(_geo_url(service, text, MAX_SUGGESTIONS), timeout=SUGGEST_TIMEOUT_S)
            return tuple(_feature_to_place(f, text) for f in data["features"])
        except (KeyError, IndexError, ValueError, TypeError, OSError) as err:
            _note_failure(service, err)
    return None


def suggest_places(text: str, online: bool = True) -> tuple:
    """Up to MAX_SUGGESTIONS places matching what the Commuter has typed so far.

    With online=False nothing is sent anywhere: sample places plus answers already known
    (so the list can appear at once). With online=True, and a key set, OpenRouteService
    autocomplete is asked too, from ONLINE_MIN_CHARS characters, unless it is paused after a
    quota answer. A failed or malformed answer leaves what was known.
    """
    text = " ".join(text.split())[:100]
    if len(text) < MIN_SUGGEST_CHARS:
        return ()
    samples = _sample_matches(text)
    remote = _suggest_cache.get(text.lower())
    if remote is None:
        remote = _places_from_payload(_stored("suggest", text.lower()))  # asked and answered before, perhaps last week
        if remote is not None:
            _suggest_cache[text.lower()] = remote
    if remote is None:
        remote = _quick_remote(text)
        if online and _api_key() and len(text) >= ONLINE_MIN_CHARS and len(samples) < MAX_SUGGESTIONS and not search_paused():
            fresh = _ask_remote(text)
            if fresh is not None:
                remote = fresh
                if len(_suggest_cache) >= _CACHE_LIMIT:
                    _suggest_cache.clear()
                _suggest_cache[text.lower()] = remote
                _store("suggest", text.lower(), {"places": [_place_to_dict(p) for p in remote]})
    return _merge(samples, remote)


def _same_place(a: Place, b: Place) -> bool:
    first = lambda label: label.split(",")[0].strip().lower()  # noqa: E731
    return first(a.label) == first(b.label) and _haversine_km(a, b) < 0.5


def _feature_to_place(feature: dict, fallback_label: str) -> Place:
    lon, lat = feature["geometry"]["coordinates"]  # GeoJSON order: lon, lat
    return Place(
        label=feature["properties"].get("label", fallback_label),
        lon=float(lon),
        lat=float(lat),
        source="OpenRouteService geocoder",
    )


def _api_key() -> str:
    return os.environ.get("ORS_API_KEY", "").strip()


def place_search_is_live() -> bool:
    """True when place search and routes use OpenRouteService (a key is set)."""
    return bool(_api_key())


_pool_lock = threading.Lock()
_idle = {}  # (scheme, host) -> connections that are open and free; shared by every thread
MAX_IDLE = 4


def _acquire(scheme: str, host: str, timeout: float, fresh: bool = False):
    """A free open connection to the host, or a new one. The web server runs each request in its
    own thread, so the connections are shared across threads rather than kept per thread."""
    key = (scheme, host)
    with _pool_lock:
        waiting = _idle.get(key, [])
        conn = None if fresh or not waiting else waiting.pop()
    if conn is None:
        cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        conn = cls(host, timeout=timeout)
    conn.timeout = timeout
    if conn.sock is not None:
        conn.sock.settimeout(timeout)
    return conn


def _release(scheme: str, host: str, conn) -> None:
    with _pool_lock:
        waiting = _idle.setdefault((scheme, host), [])
        if len(waiting) < MAX_IDLE:
            waiting.append(conn)
            return
    conn.close()


def _http_json(url: str, headers=None, body=None, timeout=None):
    """GET (no body) or POST (JSON body) and return parsed JSON. Raises on any failure.

    Connections are kept open and reused, which saves the TLS handshake on every request. If
    the server closed one while it sat idle, the request is sent once more on a new one.
    HTTP errors raise urllib.error.HTTPError, as before.
    """
    timeout = TIMEOUT_S if timeout is None else timeout
    parts = urllib.parse.urlsplit(url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    data = json.dumps(body).encode() if body is not None else None
    # No Accept header of our own: the GeoJSON route service answers "406 Not Acceptable" to application/json.
    sent_headers = dict(headers or {})
    method = "POST" if data is not None else "GET"
    for attempt in (0, 1):
        conn = _acquire(parts.scheme, parts.netloc, timeout, fresh=attempt == 1)
        reused = conn.sock is not None
        try:
            conn.request(method, target, body=data, headers=sent_headers)
            resp = conn.getresponse()
            payload = resp.read()
        except (http.client.HTTPException, OSError):
            conn.close()
            if attempt == 0 and reused:
                continue  # an idle connection the server had closed: try once on a fresh one
            raise
        if resp.will_close:
            conn.close()
        else:
            _release(parts.scheme, parts.netloc, conn)
        if resp.status >= 400:
            raise urllib.error.HTTPError(url, resp.status, resp.reason, resp.msg, io.BytesIO(payload))
        return json.loads(payload)


def warm_up() -> None:
    """Open the connection to the online service ahead of the first keystroke (the root path costs no quota)."""
    if not _api_key():
        return
    try:
        _http_json(f"{ORS_BASE}/", timeout=SUGGEST_TIMEOUT_S * 2)
    except (ValueError, OSError):
        pass  # a 404 or a reply that is not JSON still leaves the connection open and ready


def _paused(service: str) -> bool:
    return time.monotonic() < _paused_until[service]


def _note_failure(service: str, err: Exception) -> None:
    """A quota or rate-limit answer pauses that service for COOLDOWN_S instead of retrying every keystroke."""
    if isinstance(err, urllib.error.HTTPError) and err.code in (403, 429):
        _paused_until[service] = time.monotonic() + COOLDOWN_S


def search_paused() -> bool:
    """True while online suggestions are being left alone: both the autocomplete and the search
    service have answered "quota exceeded" or "too many requests" within the last minute."""
    return _paused("autocomplete") and _paused("search")


def _haversine_km(a: Place, b: Place) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi, dlmb = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


@realizes("UC.3.3")
def geocode(text: str):
    """Resolve free text to a Place, or None when nothing matches."""
    text = " ".join(text.split())
    if not text:
        return None
    here = _MY_LOCATION.match(text)
    if here:
        lat, lon = float(here.group(1)), float(here.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return Place(label=text, lon=lon, lat=lat, source="your device location")
        return None
    picked = _place_cache.get(text.lower())  # a label the Commuter chose from the suggestions
    if picked is None and _backend is not None:
        stored = _stored("place", text.lower())
        picked = _place_from_dict(stored) if stored else None
    if picked is not None:
        return picked
    matches = _sample_matches(text)
    for place in matches:
        if place.label.lower() == text.lower():
            return place
    if not _api_key() or _paused("search"):
        return matches[0] if len(matches) == 1 else None  # "upson" alone is unambiguous
    found = _places_from_payload(_stored("suggest", "search:" + text.lower()))
    if found:
        return found[0]
    try:
        data = _http_json(_geo_url("search", text, 1))
        if data["features"]:
            place = _feature_to_place(data["features"][0], text)
            _store("suggest", "search:" + text.lower(), {"places": [_place_to_dict(place)]})
            _store("place", place.label.lower(), _place_to_dict(place))
            return place
        return matches[0] if len(matches) == 1 else None
    except (KeyError, IndexError, ValueError, TypeError, OSError) as err:
        _note_failure("search", err)
        return matches[0] if len(matches) == 1 else None


def _thin(points: list) -> tuple:
    """Keep a long path drawable: at most MAX_PATH_POINTS points, always the first and last."""
    if len(points) > MAX_PATH_POINTS:
        step = math.ceil(len(points) / MAX_PATH_POINTS)
        points = points[::step] + ([points[-1]] if (len(points) - 1) % step else [])
    return tuple(points)


def _ors_route(mode: str, origin: Place, dest: Place) -> RouteOption:
    data = _http_json(
        f"{ORS_BASE}/v2/directions/{PROFILES[mode]}/geojson",
        headers={"Authorization": _api_key(), "Content-Type": "application/json"},
        body={"coordinates": [[origin.lon, origin.lat], [dest.lon, dest.lat]]},
    )
    feature = data["features"][0]
    summary = feature["properties"]["summary"]
    path = _thin([(float(lat), float(lon)) for lon, lat in feature["geometry"]["coordinates"]])  # GeoJSON: lon, lat
    if len(path) < 2:
        raise ValueError("route has no line")
    return RouteOption(
        mode=mode,
        distance_km=round(float(summary["distance"]) / 1000, 2),  # metres -> km
        duration_min=round(float(summary["duration"]) / 60, 1),  # seconds -> min
        source="OpenRouteService",
        path=path,
    )


def _fallback_route(mode: str, origin: Place, dest: Place) -> RouteOption:
    km = round(_haversine_km(origin, dest) * FALLBACK_DETOUR[mode], 2)
    return RouteOption(
        mode=mode,
        distance_km=km,
        duration_min=round(km / FALLBACK_SPEED_KMH[mode] * 60, 1),
        source=FALLBACK_SOURCE,
        path=((origin.lat, origin.lon), (dest.lat, dest.lon)),  # a straight line, not a route
    )


@realizes("UC.3.3")
def get_route_options(origin: Place, dest: Place) -> tuple:
    """One RouteOption per mode; a mode whose ORS call fails falls back individually.

    Answers that came entirely from ORS are remembered, so previewing the routes on the map
    and then comparing them uses one set of requests.
    """
    key = tuple(round(v, 5) for v in (origin.lat, origin.lon, dest.lat, dest.lon))
    if key in _route_cache:
        return _route_cache[key]
    keep = _backend is not None and _is_known(origin) and _is_known(dest)  # never a position someone is standing at
    stored_key = "|".join(f"{v:.4f}" for v in key)
    if keep:
        stored = _stored("route", stored_key)
        try:
            from_disk = tuple(_route_from_dict(d) for d in stored["routes"]) if stored else ()
        except (KeyError, TypeError, ValueError):
            from_disk = ()
        if len(from_disk) == len(PROFILES) and all(o.source == "OpenRouteService" for o in from_disk):
            _route_cache[key] = from_disk
            return from_disk
    def one(mode: str) -> RouteOption:
        if _api_key() and not _paused("route"):
            try:
                return _ors_route(mode, origin, dest)
            except (KeyError, IndexError, ValueError, TypeError, OSError) as err:
                _note_failure("route", err)
        return _fallback_route(mode, origin, dest)

    result = tuple(_route_pool.map(one, PROFILES))  # the three requests wait on the network, so run side by side
    if all(o.source == "OpenRouteService" for o in result):
        if len(_route_cache) >= _CACHE_LIMIT:
            _route_cache.clear()
        _route_cache[key] = result
        if keep:
            _store("route", stored_key, {"routes": [_route_to_dict(o) for o in result]})
    return result
