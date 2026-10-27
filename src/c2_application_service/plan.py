from src.c2_application_service.comparison import compare_modes
from src.c2_application_service.recommendation import recommend_mode
from src.c3_data_adapter import current_weather
from src.interfaces import CommutePlan
from src.model_trace import realizes

VEHICLES = ("bike", "scooter")  # the student has neither unless they say so


@realizes("UC.3.5")
def plan_commute(origin_text: str, destination_text: str, have=()) -> CommutePlan:
    """Compare the ways the Commuter can use, apply weather and time checks, and recommend one.

    Drive and walk are always compared; a bike or scooter only when listed in `have`.
    Weather is the current condition at the start place; if it cannot be fetched the
    recommendation still works and says the weather rules were not applied.
    """
    comparisons, origin, dest, errors = compare_modes(origin_text, destination_text)
    if errors:
        return CommutePlan(origin, dest, (), None, tuple(errors))
    usable = tuple(c for c in comparisons if c.mode not in VEHICLES or c.mode in have)
    weather = current_weather(origin)
    return CommutePlan(origin, dest, usable, recommend_mode(usable, weather), ())
