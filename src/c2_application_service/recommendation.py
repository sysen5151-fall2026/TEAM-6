from src.c4_explanation_model import explain_recommendation
from src.interfaces import ModeComparison, Recommendation

# Feasibility thresholds. PROJECT ASSUMPTIONS, not safety guidance: they decide which
# modes are offered, and the page shows the reason for every mode that is ruled out.
RAIN_MM = 0.1  # walking and cycling are ruled out at or above this precipitation
FREEZING_C = 0.0  # cycling is ruled out at or below this temperature (ice)
BIKE_WIND_KMH = 40.0  # cycling is ruled out at or above this wind speed
DEFAULT_MAX_EXTRA_MIN = 10.0  # most extra minutes over the fastest mode the Commuter accepts

OUTDOOR_MODES = ("walk", "bike")


def _weather_note(weather) -> str:
    if weather is None:
        return "Weather was not available, so no weather rules were applied."
    parts = [f"{weather.precipitation_mm:g} mm precipitation"]
    if weather.temperature_c is not None:
        parts.append(f"{weather.temperature_c:g} C")
    if weather.wind_kmh is not None:
        parts.append(f"wind {weather.wind_kmh:g} km/h")
    return "Weather at the start (current conditions): " + ", ".join(parts) + "."


def _exclusion(row: ModeComparison, weather, not_feasible, fastest_min, max_extra_min):
    """Return the reason this mode is ruled out, or "" when it stays eligible."""
    if row.mode in not_feasible:
        return "you marked it not feasible"
    if weather is not None and row.mode in OUTDOOR_MODES and weather.precipitation_mm >= RAIN_MM:
        return f"rain ({weather.precipitation_mm:g} mm, limit {RAIN_MM:g} mm)"
    if weather is not None and row.mode == "bike":
        if weather.temperature_c is not None and weather.temperature_c <= FREEZING_C:
            return f"freezing ({weather.temperature_c:g} C, limit {FREEZING_C:g} C)"
        if weather.wind_kmh is not None and weather.wind_kmh >= BIKE_WIND_KMH:
            return f"strong wind ({weather.wind_kmh:g} km/h, limit {BIKE_WIND_KMH:g} km/h)"
    extra = row.duration_min - fastest_min
    if extra > max_extra_min:
        return f"{extra:g} min more than the fastest, over your {max_extra_min:g} min limit"
    return ""


def recommend_mode(comparisons, weather, not_feasible=(), max_extra_min=DEFAULT_MAX_EXTRA_MIN):
    """Filter modes by feasibility, then pick the lowest CO2e (ties: faster).

    Deterministic: the same inputs always give the same answer. A mode the Commuter
    marked not feasible is never recommended. Returns a Recommendation.
    """
    note = _weather_note(weather)
    fastest = min(comparisons, key=lambda c: (c.duration_min, c.mode))
    excluded, eligible = [], []
    for row in comparisons:
        reason = _exclusion(row, weather, not_feasible, fastest.duration_min, max_extra_min)
        if reason:
            excluded.append((row.mode, reason))
        else:
            eligible.append(row)

    met_limits = bool(eligible)
    if not eligible:  # nothing met every limit: fall back to the fastest the user has not ruled out
        eligible = [c for c in comparisons if c.mode not in not_feasible]
    if not eligible:
        return Recommendation("", "Every mode is marked not feasible in your settings.", tuple(excluded), note)

    chosen = min(eligible, key=lambda c: (c.co2e_g, c.duration_min, c.mode))
    if not met_limits:
        chosen = min(eligible, key=lambda c: (c.duration_min, c.mode))
    reason = explain_recommendation(chosen, fastest, met_limits)
    return Recommendation(chosen.mode, reason, tuple(excluded), note)
