from datetime import datetime

from src.c2_application_service.bus_planner import find_bus, local_now
from src.c2_application_service.comparison import bus_comparison, compare_modes
from src.c2_application_service.recommendation import recommend_mode
from src.c3_data_adapter import current_weather
from src.interfaces import CommutePlan
from src.model_trace import realizes

VEHICLES = ("bike", "scooter")  # the student has neither unless they say so


@realizes("UC.3.5")
def plan_commute(origin_text: str, destination_text: str, have=(), when: datetime = None, bus_route: str = "") -> CommutePlan:
    """Compare the ways the Commuter can use, apply weather and time checks, and recommend one.

    Drive and walk are always compared; a bike or scooter only when listed in `have`; the
    bus when the TCAT schedule has a direct ride leaving at or after `when` (default: now,
    Ithaca time). When several routes link the places, `bus_route` picks which one the bus
    row is built from (default: the one that arrives first). Weather is the current condition at the start place; if it cannot be
    fetched the recommendation still works and says the weather rules were not applied.
    """
    when = when or local_now()
    comparisons, origin, dest, errors = compare_modes(origin_text, destination_text)
    if errors:
        return CommutePlan(origin, dest, (), None, tuple(errors))
    usable = tuple(c for c in comparisons if c.mode not in VEHICLES or c.mode in have)
    bus = find_bus(origin, dest, when)
    rows, choice = (), ""
    if bus.options:
        drive = next(c for c in comparisons if c.mode == "drive")
        rows = tuple(bus_comparison(option, drive) for option in bus.options)
        chosen = next((i for i, o in enumerate(bus.options) if o.route_id == bus_route), 0)  # else the best
        choice = bus.options[chosen].route_id
        usable += (rows[chosen],)
    weather = current_weather(origin)
    return CommutePlan(origin, dest, usable, recommend_mode(usable, weather), (), bus, rows, choice)
