from datetime import date

from src.c2_application_service.achievements import evaluate_badges
from src.c2_application_service.plan import plan_commute
from src.c3_data_adapter import add_confirmed, confirmed_trips
from src.interfaces import ConfirmedTrip, ModeComparison
from src.model_trace import realizes


MIN_PEOPLE, MAX_PEOPLE = 2, 8  # a carpool, the Commuter included (a car or a van)


def _earned(trips, community=()) -> dict:
    return {b.id: b.name for b in evaluate_badges(trips, community) if b.earned}


@realizes("UC.3.8")
def confirm_trip(origin_text: str, destination_text: str, mode: str, day: str, have=(), when=None, occupants: int = 1, bus_route: str = "", trips=None,
                 community=()):
    """Record a trip the Commuter says they took, in `trips` (their store; default the in-memory one).

    `community` is what everyone else has confirmed, for the shared tree when badges are worked out.

    The distance and emissions are recomputed here from the places and mode, never
    taken from the browser. Returns (trip or None, names of newly earned badges, errors).
    """
    try:
        trip_date = date.fromisoformat(day)
    except ValueError:
        return None, (), ["Enter the trip date as YYYY-MM-DD."]
    if trip_date > date.today():
        return None, (), ["A trip that has not happened yet can't be confirmed."]

    carpool = mode == "carpool"
    if carpool and not MIN_PEOPLE <= occupants <= MAX_PEOPLE:
        return None, (), [f"A carpool needs {MIN_PEOPLE} to {MAX_PEOPLE} people, you included."]

    plan = plan_commute(origin_text, destination_text, have=have, when=when, bus_route=bus_route)
    if plan.errors:
        return None, (), list(plan.errors)
    row = next((c for c in plan.comparisons if c.mode == ("drive" if carpool else mode)), None)
    if row is None:
        return None, (), ["That mode isn't one of the compared options."]
    if carpool:  # the same car and route, so each person's share is the drive emissions over the people in it
        share_g = round(row.co2e_g / occupants)
        row = ModeComparison("carpool", row.distance_km, row.duration_min, share_g, row.co2e_g - share_g, row.source)

    trip = ConfirmedTrip(
        date=day,
        mode=mode,
        origin=plan.origin.label,
        destination=plan.destination.label,
        distance_km=row.distance_km,
        co2e_g=row.co2e_g,
        difference_g=row.difference_g,
        recommended_mode=plan.recommendation.mode,
        occupants=occupants if carpool else 1,
        route=next((o.route_name for o in plan.bus.options if o.route_id == plan.bus_choice), "") if mode == "bus" and plan.bus else "",
    )
    before = _earned(confirmed_trips(trips), community)
    if not add_confirmed(trip, trips):
        return None, (), ["You already confirmed this trip for that date."]
    after = _earned(confirmed_trips(trips), community)
    return trip, tuple(name for id_, name in after.items() if id_ not in before), []
