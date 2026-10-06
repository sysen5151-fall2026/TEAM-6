from src.interfaces import (
    CommuteRequest,
    EmissionFactor,
    TrendSummary,
    TripRecord,
    WeatherForecast,
    WeatherQuery,
)
from src.model_trace import realizes
from src.x3_open_meteo_stub import return_weather_forecast

# STUB DATA: placeholder values, NOT reviewed emission factors. SRD 2.4.1 (reviewed
# factors with source/units/geography/version) is not yet satisfied; the Method
# Reviewer (Yinping Yin, SH.4) must supply the real table before M2.
_PLACEHOLDER_FACTORS = {
    "drive": 192.0,
    "carpool": 96.0,
    "bus": 105.0,
    "bike": 0.0,
    "walk": 0.0,
}

_TRIPS = []  # in-memory stand-in for the SQLite/trip store


@realizes("UC.1.5")
def retrieve_factor(request: CommuteRequest) -> EmissionFactor:
    """UC.1.5 (second half) Accept Entry and Retrieve Factor - STUB lookup."""
    return EmissionFactor(
        mode=request.mode,
        g_co2e_per_km=_PLACEHOLDER_FACTORS[request.mode],
        units="g CO2e per vehicle-km (placeholder)",
        geography="US (placeholder)",
        source="PLACEHOLDER - not a reviewed factor",
        version="stub-0",
    )


@realizes("UC.1.6")
def request_weather(query: WeatherQuery) -> WeatherForecast:
    """UC.1.6 Request Weather - C.0 sends the Weather Query to X.3 via C.3."""
    return return_weather_forecast(query)


@realizes("UC.1.8")
def store_trip(request: CommuteRequest, co2e_g: float) -> TripRecord:
    """UC.1.8 (second half) Store Trip - STUB in-memory store."""
    record = TripRecord(request=request, co2e_g=co2e_g)
    _TRIPS.append(record)
    return record


@realizes("UC.1.9")
def update_trends(baseline_co2e_g: float) -> TrendSummary:
    """UC.1.9 (first half) Update Trends - STUB: sums the in-memory trips.

    Weekly = monthly = all stored trips; no date windowing yet (SRD 2.1.6 is
    only partially exercised by the skeleton).
    """
    total = sum(t.co2e_g for t in _TRIPS)
    return TrendSummary(
        weekly_total_g=total,
        monthly_total_g=total,
        cumulative_difference_g=baseline_co2e_g * len(_TRIPS) - total,
    )


def reset_store() -> None:
    """Test helper only; not part of the modeled behavior."""
    _TRIPS.clear()
