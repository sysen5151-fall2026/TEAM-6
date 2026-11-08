"""Current weather at a place, from Open-Meteo (free, no key), for C.3.

Checked once against the live service on 2026-10-27 (the `current` block with
temperature_2m, precipitation and wind_speed_10m). Returns None on any failure
so callers can say the weather was not applied instead of failing.
"""

import urllib.parse

from src.c3_data_adapter.route_adapter import _http_json
from src.interfaces import Place, WeatherForecast

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def current_weather(place: Place):
    query = urllib.parse.urlencode(
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "current": "temperature_2m,precipitation,wind_speed_10m",
            "timezone": "auto",
        }
    )
    try:
        current = _http_json(f"{OPEN_METEO_URL}?{query}")["current"]
        return WeatherForecast(
            precipitation_mm=float(current["precipitation"]),
            forecast_timestamp=str(current["time"]),
            temperature_c=float(current["temperature_2m"]),
            wind_kmh=float(current["wind_speed_10m"]),
        )
    except (KeyError, ValueError, TypeError, OSError):
        return None
