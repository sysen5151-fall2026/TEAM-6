from src.c3_data_adapter import request_weather, retrieve_factor, store_trip, update_trends
from src.c4_explanation_model import explain_result
from src.interfaces import (
    CommuteImpactResult,
    CommuteRequest,
    EmissionFactor,
    TrendSummary,
    WeatherForecast,
    WeatherQuery,
)
from src.model_trace import realizes

DISTANCE_CONVENTION = "one-way distance per logged trip"
LOWER_EMISSION_MODES = ("walk", "bike")  # product-description example rule
SHORT_TRIP_KM = 3.0  # "distance under 3 km and no rain" - rule to be validated (BMA 7.8)


@realizes("UC.1.5")
def process_commute(request: CommuteRequest) -> CommuteImpactResult:
    """UC.1.5 Accept Entry and Retrieve Factor, then drive UC.1.6-UC.1.11.

    Single entry point of C.2. Order follows the Sequence Diagram (BMA 7.7):
    factor -> weather -> estimate/store -> trends/baseline -> alternatives -> result.
    """
    factor = retrieve_factor(request)  # UC.1.5 (SRD 2.4.1 - stubbed factor)
    forecast = request_weather(  # UC.1.6 -> UC.1.7 (X.3 stub)
        WeatherQuery(coarse_area=request.coarse_area, date=request.date)
    )
    estimated_g = estimate_emissions(request, factor)  # UC.1.8
    store_trip(request, estimated_g)  # UC.1.8
    baseline_g, trend = compare_baseline(request, estimated_g)  # UC.1.9
    alt_mode, alt_reason = evaluate_alternatives(request, forecast)  # UC.1.10
    return CommuteImpactResult(  # UC.1.11 payload; C.1 displays it
        estimated_co2e_g=estimated_g,
        baseline_co2e_g=baseline_g,
        estimated_difference_g=baseline_g - estimated_g,
        difference_label="estimated difference",
        factor_source=factor.source,
        factor_version=factor.version,
        distance_convention=DISTANCE_CONVENTION,
        trend=trend,
        alternative_mode=alt_mode,
        alternative_reason=alt_reason,
        explanation=explain_result(),
    )


@realizes("UC.1.8")
def estimate_emissions(request: CommuteRequest, factor: EmissionFactor) -> float:
    """UC.1.8 (first half) Estimate Emissions - SRD 2.1.2 / 2.4.2.

    Distance x factor. Occupancy handling is NOT implemented yet (BMA 7.8 open item).
    """
    return round(request.distance_km * factor.g_co2e_per_km)


@realizes("UC.1.9")
def compare_baseline(request: CommuteRequest, estimated_g: float):
    """UC.1.9 Update Trends and Compare Baseline - SRD 2.4.3 / 2.1.6.

    Always-drive baseline: same distance, declared vehicle factor, occupancy 1.
    """
    drive_factor = retrieve_factor(
        CommuteRequest(
            mode="drive",
            distance_km=request.distance_km,
            date=request.date,
            coarse_area=request.coarse_area,
        )
    )
    baseline_g = round(request.distance_km * drive_factor.g_co2e_per_km)
    trend: TrendSummary = update_trends(baseline_g)
    return baseline_g, trend


@realizes("UC.1.10")
def evaluate_alternatives(request: CommuteRequest, forecast: WeatherForecast):
    """UC.1.10 Evaluate Feasible Alternatives - SRD 2.1.4 and 2.1.5.

    Deterministic rule: trip under 3 km and no rain -> walk, else bike; modes the
    Commuter marked not feasible are never recommended (2.1.5).
    Returns (mode, reason); ("", reason) when there is no eligible option.
    """
    if request.mode in LOWER_EMISSION_MODES:
        return "", "You already used a lowest-emission mode."
    if request.distance_km >= SHORT_TRIP_KM or forecast.precipitation_mm > 0:
        return "", "Distance or forecast weather does not suit walking or cycling."
    for mode in LOWER_EMISSION_MODES:
        if mode not in request.not_feasible_modes:
            return mode, (
                f"The trip is {request.distance_km:g} km (under {SHORT_TRIP_KM:g} km) "
                f"and the forecast shows {forecast.precipitation_mm:g} mm of rain."
            )
    return "", "Walking and cycling are marked not feasible in your settings."
