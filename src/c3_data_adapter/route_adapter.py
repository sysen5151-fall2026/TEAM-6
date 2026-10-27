"""Place search and per-mode routes for C.3.

Uses OpenRouteService (ORS) when the ORS_API_KEY environment variable is set.
Without a key, or when a call fails, it falls back to a clearly labelled
estimate from sample places so the page keeps working.

Checked once against the live service on 2026-10-27 (geocode search and the
three Directions profiles on api.openrouteservice.org, free key). The unit
tests still use mocked responses; no automated test calls the network.
"""

import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from src.interfaces import Place, RouteOption
from src.model_trace import realizes

# ORS announced a move to api.heigit.org; the same paths returned 404 there on 2026-10-27,
# so the old host stays the default and ORS_BASE_URL can switch it without a code change.
ORS_BASE = os.environ.get("ORS_BASE_URL", "https://api.openrouteservice.org").rstrip("/")
TIMEOUT_S = 5

PROFILES = {"drive": "driving-car", "walk": "foot-walking", "bike": "cycling-regular"}

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


def suggest_places(text: str) -> tuple:
    """Up to MAX_SUGGESTIONS places matching what the Commuter has typed so far.

    Sample places come first (instant, offline), then OpenRouteService autocomplete when
    a key is set. A failed or malformed ORS answer leaves just the sample matches.
    """
    text = " ".join(text.split())[:100]
    if len(text) < MIN_SUGGEST_CHARS:
        return ()
    found = list(_sample_matches(text))
    if _api_key() and len(found) < MAX_SUGGESTIONS:
        remote = _suggest_cache.get(text.lower())
        if remote is None:
            query = urllib.parse.urlencode(
                {
                    "api_key": _api_key(),
                    "text": text,
                    "size": MAX_SUGGESTIONS,
                    "focus.point.lon": FOCUS_LON,
                    "focus.point.lat": FOCUS_LAT,
                }
            )
            try:
                data = _http_json(f"{ORS_BASE}/geocode/autocomplete?{query}")
                remote = tuple(_feature_to_place(f, text) for f in data["features"])
                if len(_suggest_cache) >= _CACHE_LIMIT:
                    _suggest_cache.clear()
                _suggest_cache[text.lower()] = remote
            except (KeyError, IndexError, ValueError, TypeError, OSError):
                remote = ()
        # A routed result for the same named place (within 0.5 km) replaces the sample entry.
        found = [s for s in found if not any(_same_place(s, r) for r in remote)] + list(remote)
    seen, unique = set(), []
    for place in found:
        if place.label.lower() not in seen:
            seen.add(place.label.lower())
            unique.append(place)
    for place in unique[:MAX_SUGGESTIONS]:
        _remember(place)
    return tuple(unique[:MAX_SUGGESTIONS])


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


def _http_json(url: str, headers=None, body=None):
    """GET (no body) or POST (JSON body) and return parsed JSON. Raises on any failure."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)


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
    if picked is not None:
        return picked
    matches = _sample_matches(text)
    for place in matches:
        if place.label.lower() == text.lower():
            return place
    if not _api_key():
        return matches[0] if len(matches) == 1 else None  # "upson" alone is unambiguous
    query = urllib.parse.urlencode({"api_key": _api_key(), "text": text, "size": 1})
    try:
        data = _http_json(f"{ORS_BASE}/geocode/search?{query}")
        return _feature_to_place(data["features"][0], text)
    except (KeyError, IndexError, ValueError, TypeError, OSError):
        return None


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
    def one(mode: str) -> RouteOption:
        if _api_key():
            try:
                return _ors_route(mode, origin, dest)
            except (KeyError, IndexError, ValueError, TypeError, OSError):
                pass
        return _fallback_route(mode, origin, dest)

    with ThreadPoolExecutor(max_workers=len(PROFILES)) as pool:  # the three requests wait on the network
        result = tuple(pool.map(one, PROFILES))
    if all(o.source == "OpenRouteService" for o in result):
        if len(_route_cache) >= _CACHE_LIMIT:
            _route_cache.clear()
        _route_cache[key] = result
    return result
