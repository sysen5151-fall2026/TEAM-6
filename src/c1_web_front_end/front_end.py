from src.c2_application_service import process_commute
from src.interfaces import CommuteImpactResult, CommuteRequest, EntryForm
from src.model_trace import realizes


@realizes("UC.1.2")
def present_entry_fields() -> EntryForm:
    """UC.1.2 Present Entry Fields (SRD 2.1.1, 2.1.9, 2.5.3).

    STUB: returns the field list only; there is no HTML/web layer yet.
    """
    return EntryForm(
        fields=("mode", "distance_km", "date", "occupancy", "coarse_area", "not_feasible_modes")
    )


@realizes("UC.1.4")
def submit_commute_request(request: CommuteRequest) -> CommuteImpactResult:
    """Receives the submitted Commute Request (UC.1.4) and hands it to C.2 (UC.1.5)."""
    return process_commute(request)


@realizes("UC.1.11")
def display_commute_result(result: CommuteImpactResult) -> str:
    """UC.1.11 Display Commute Result (SRD 2.1.2, 2.1.3, 2.1.6, 2.4.4).

    STUB: renders plain text instead of a web view.
    """
    lines = [
        f"Estimated CO2e for this trip: {result.estimated_co2e_g:g} g",
        f"Always-drive baseline: {result.baseline_co2e_g:g} g",
        f"{result.difference_label.capitalize()}: {result.estimated_difference_g:g} g",
        f"Weekly total: {result.trend.weekly_total_g:g} g | "
        f"Monthly total: {result.trend.monthly_total_g:g} g | "
        f"Cumulative {result.difference_label}: {result.trend.cumulative_difference_g:g} g",
        f"Factor: {result.factor_source} (version {result.factor_version}); "
        f"distance convention: {result.distance_convention}",
    ]
    if result.alternative_mode:
        lines.append(f"Suggested alternative: {result.alternative_mode} - {result.alternative_reason}")
    else:
        lines.append(f"No alternative suggested - {result.alternative_reason}")
    lines.append(result.explanation)
    return "\n".join(lines)
