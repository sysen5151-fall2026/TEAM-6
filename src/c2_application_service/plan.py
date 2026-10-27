from datetime import datetime

from src.c2_application_service.bus_planner import find_bus, local_now
from src.c2_application_service.comparison import bus_comparison, compare_modes
from src.c2_application_service.recommendation import recommend_mode
from src.c3_data_adapter import current_weather
from src.interfaces import CommutePlan
from src.model_trace import realizes

VEHICLES = ("bike", "scooter")  # the student has neither unless they say so


@realizes("UC.3.5")
def plan_commute(origin_text: str, destination_text: str, have=(), when: datetime = None) -> CommutePlan:
    """Compare the ways the Commuter can use, apply weather and time checks, and recommend one.

    Drive and walk are always compared; a bike or scooter only when listed in `have`; the
    bus when the TCAT schedule has a direct ride leaving at or after `when` (default: now,
    Ithaca time). Weather is the current condition at the start place; if it cannot be
    fetched the recommendation still works and says the weather rules were not applied.
    """
    when = when or local_now()
    comparisons, origin, dest, errors = compare_modes(origin_text, destination_text)
    if errors:
        return CommutePlan(origin, dest, (), None, tuple(errors))
    usable = tuple(c for c in comparisons if c.mode not in VEHICLES or c.mode in have)
    bus = find_bus(origin, dest, when)
    if bus.itinerary:
        drive = next(c for c in comparisons if c.mode == "drive")
        usable += (bus_comparison(bus.itinerary, drive),)
    weather = current_weather(origin)
    return CommutePlan(origin, dest, usable, recommend_mode(usable, weather), (), bus)
