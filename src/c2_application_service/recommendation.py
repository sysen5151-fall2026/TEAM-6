from src.c4_explanation_model import explain_recommendation
from src.interfaces import ModeComparison, Recommendation
from src.model_trace import realizes

# Feasibility thresholds. PROJECT ASSUMPTIONS, not safety guidance: they decide which
# modes are offered, and the page shows the reason for every mode that is ruled out.
RAIN_MM = 0.1  # walking and cycling are ruled out at or above this precipitation
FREEZING_C = 0.0  # cycling is ruled out at or below this temperature (ice)
BIKE_WIND_KMH = 40.0  # cycling is ruled out at or above this wind speed
WALK_MAX_MIN = 30.0  # a walk longer than this is ruled out
WHEELED_MAX_MIN = 45.0  # so is a bike or scooter ride longer than this

OUTDOOR_MODES = ("walk", "bike", "scooter")
WHEELED_MODES = ("bike", "scooter")  # also ruled out by ice and strong wind
# Tie-break when two ways emit the same: walk first, then bike, then the rest.
PRIORITY = ("walk", "bike", "scooter", "bus", "carpool", "drive")


def _weather_note(weather) -> str:
    if weather is None:
        return "Weather was not available, so no weather rules were applied."
    parts = [f"{weather.precipitation_mm:g} mm precipitation"]
    if weather.temperature_c is not None:
        parts.append(f"{weather.temperature_c:g} C")
    if weather.wind_kmh is not None:
        parts.append(f"wind {weather.wind_kmh:g} km/h")
    return "Weather at the start (current conditions): " + ", ".join(parts) + "."


def _exclusion(row: ModeComparison, weather, not_feasible):
    """Return the reason this mode is ruled out, or "" when it stays eligible."""
    if row.mode in not_feasible:
        return "you marked it not feasible"
    if weather is not None and row.mode in OUTDOOR_MODES and weather.precipitation_mm >= RAIN_MM:
        return f"rain ({weather.precipitation_mm:g} mm, limit {RAIN_MM:g} mm)"
    if weather is not None and row.mode in WHEELED_MODES:
        if weather.temperature_c is not None and weather.temperature_c <= FREEZING_C:
            return f"freezing ({weather.temperature_c:g} C, limit {FREEZING_C:g} C)"
        if weather.wind_kmh is not None and weather.wind_kmh >= BIKE_WIND_KMH:
            return f"strong wind ({weather.wind_kmh:g} km/h, limit {BIKE_WIND_KMH:g} km/h)"
    cap = WALK_MAX_MIN if row.mode == "walk" else WHEELED_MAX_MIN if row.mode in WHEELED_MODES else None
    if cap is not None and row.duration_min > cap:
        return f"{row.duration_min:g} min is over the {cap:g} min limit for {row.mode}"
    return ""


def _rank(mode: str) -> int:
    return PRIORITY.index(mode) if mode in PRIORITY else len(PRIORITY)


@realizes("UC.3.5")
def recommend_mode(comparisons, weather, not_feasible=()):
    """Filter modes by weather and time, then pick the lowest CO2e (ties: walk, bike, scooter ...).

    Deterministic: the same inputs always give the same answer. A mode named in
    not_feasible is never recommended. Returns a Recommendation.
    """
    note = _weather_note(weather)
    fastest = min(comparisons, key=lambda c: (c.duration_min, c.mode))
    excluded, eligible = [], []
    for row in comparisons:
        reason = _exclusion(row, weather, not_feasible)
        if reason:
            excluded.append((row.mode, reason))
        else:
            eligible.append(row)

    met_limits = bool(eligible)
    if not eligible:  # nothing met every limit: fall back to the fastest the user has not ruled out
        eligible = [c for c in comparisons if c.mode not in not_feasible]
    if not eligible:
        return Recommendation("", "Every mode is marked not feasible.", tuple(excluded), note)

    chosen = min(eligible, key=lambda c: (c.co2e_g, _rank(c.mode), c.duration_min, c.mode))
    if not met_limits:
        chosen = min(eligible, key=lambda c: (c.duration_min, c.mode))
    reason = explain_recommendation(chosen, fastest, met_limits)
    return Recommendation(chosen.mode, reason, tuple(excluded), note)
