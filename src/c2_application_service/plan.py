from src.c2_application_service.comparison import compare_modes
from src.c2_application_service.recommendation import DEFAULT_MAX_EXTRA_MIN, recommend_mode
from src.c3_data_adapter import current_weather
from src.interfaces import CommutePlan


def plan_commute(
    origin_text: str,
    destination_text: str,
    not_feasible=(),
    max_extra_min=DEFAULT_MAX_EXTRA_MIN,
    transit_minutes=None,
) -> CommutePlan:
    """Compare modes, apply weather and the Commuter's limits, and recommend one.

    Weather is the current condition at the start place; if it cannot be fetched the
    recommendation still works and says the weather rules were not applied.
    """
    comparisons, origin, dest, errors = compare_modes(origin_text, destination_text, transit_minutes)
    if errors:
        return CommutePlan(origin, dest, (), None, tuple(errors))
    weather = current_weather(origin)
    recommendation = recommend_mode(comparisons, weather, tuple(not_feasible), max_extra_min)
    return CommutePlan(origin, dest, comparisons, recommendation, ())
