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
import urllib.error
import urllib.parse
import urllib.request

from src.interfaces import Place, RouteOption

# ORS announced a move to api.heigit.org; the same paths returned 404 there on 2026-10-27,
# so the old host stays the default and ORS_BASE_URL can switch it without a code change.
ORS_BASE = os.environ.get("ORS_BASE_URL", "https://api.openrouteservice.org").rstrip("/")
TIMEOUT_S = 5

PROFILES = {"drive": "driving-car", "walk": "foot-walking", "bike": "cycling-regular"}

# Fallback assumptions (NOT measured): road distance = straight line x detour factor.
FALLBACK_DETOUR = {"drive": 1.3, "walk": 1.2, "bike": 1.25}
FALLBACK_SPEED_KMH = {"drive": 30.0, "walk": 5.0, "bike": 15.0}
FALLBACK_SOURCE = "estimate (straight line x detour factor), not a routed distance"

# Approximate coordinates, for the offline fallback only.
SAMPLE_PLACES = {
    "Cornell Arts Quad": (42.4491, -76.4835),
    "Collegetown": (42.4421, -76.4853),
    "Ithaca Commons": (42.4396, -76.4968),
    "Cornell Gates Hall": (42.4446, -76.4818),
}


def sample_places() -> tuple:
    return tuple(SAMPLE_PLACES)


def _api_key() -> str:
    return os.environ.get("ORS_API_KEY", "").strip()


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


def geocode(text: str):
    """Resolve free text to a Place, or None when nothing matches."""
    text = text.strip()
    if not text:
        return None
    for name, (lat, lon) in SAMPLE_PLACES.items():
        if name.lower() == text.lower():
            return Place(label=name, lon=lon, lat=lat, source="sample place list")
    if not _api_key():
        return None
    query = urllib.parse.urlencode({"api_key": _api_key(), "text": text, "size": 1})
    try:
        data = _http_json(f"{ORS_BASE}/geocode/search?{query}")
        feature = data["features"][0]
        lon, lat = feature["geometry"]["coordinates"]  # GeoJSON order: lon, lat
        return Place(
            label=feature["properties"].get("label", text),
            lon=float(lon),
            lat=float(lat),
            source="OpenRouteService geocoder",
        )
    except (KeyError, IndexError, ValueError, TypeError, OSError):
        return None


def _ors_route(mode: str, origin: Place, dest: Place) -> RouteOption:
    data = _http_json(
        f"{ORS_BASE}/v2/directions/{PROFILES[mode]}",
        headers={"Authorization": _api_key(), "Content-Type": "application/json"},
        body={"coordinates": [[origin.lon, origin.lat], [dest.lon, dest.lat]]},
    )
    summary = data["routes"][0]["summary"]
    return RouteOption(
        mode=mode,
        distance_km=round(float(summary["distance"]) / 1000, 2),  # metres -> km
        duration_min=round(float(summary["duration"]) / 60, 1),  # seconds -> min
        source="OpenRouteService",
    )


def _fallback_route(mode: str, origin: Place, dest: Place) -> RouteOption:
    km = round(_haversine_km(origin, dest) * FALLBACK_DETOUR[mode], 2)
    return RouteOption(
        mode=mode,
        distance_km=km,
        duration_min=round(km / FALLBACK_SPEED_KMH[mode] * 60, 1),
        source=FALLBACK_SOURCE,
    )


def get_route_options(origin: Place, dest: Place) -> tuple:
    """One RouteOption per mode; a mode whose ORS call fails falls back individually."""
    options = []
    for mode in PROFILES:
        if _api_key():
            try:
                options.append(_ors_route(mode, origin, dest))
                continue
            except (KeyError, IndexError, ValueError, TypeError, OSError):
                pass
        options.append(_fallback_route(mode, origin, dest))
    return tuple(options)
