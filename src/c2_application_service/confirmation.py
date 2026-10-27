from datetime import date

from src.c2_application_service.achievements import evaluate_badges
from src.c2_application_service.plan import plan_commute
from src.c3_data_adapter import add_confirmed, confirmed_trips
from src.interfaces import ConfirmedTrip
from src.model_trace import realizes


def _earned(trips) -> dict:
    return {b.id: b.name for b in evaluate_badges(trips) if b.earned}


@realizes("UC.3.8")
def confirm_trip(origin_text: str, destination_text: str, mode: str, day: str, transit_minutes=None):
    """Record a trip the Commuter says they took.

    The distance and emissions are recomputed here from the places and mode, never
    taken from the browser. Returns (trip or None, names of newly earned badges, errors).
    """
    try:
        trip_date = date.fromisoformat(day)
    except ValueError:
        return None, (), ["Enter the trip date as YYYY-MM-DD."]
    if trip_date > date.today():
        return None, (), ["A trip that has not happened yet can't be confirmed."]

    plan = plan_commute(origin_text, destination_text, transit_minutes=transit_minutes)
    if plan.errors:
        return None, (), list(plan.errors)
    row = next((c for c in plan.comparisons if c.mode == mode), None)
    if row is None:
        return None, (), ["That mode isn't one of the compared options."]

    trip = ConfirmedTrip(
        date=day,
        mode=mode,
        origin=plan.origin.label,
        destination=plan.destination.label,
        distance_km=row.distance_km,
        co2e_g=row.co2e_g,
        difference_g=row.difference_g,
        recommended_mode=plan.recommendation.mode,
    )
    before = _earned(confirmed_trips())
    if not add_confirmed(trip):
        return None, (), ["You already confirmed this trip for that date."]
    after = _earned(confirmed_trips())
    return trip, tuple(name for id_, name in after.items() if id_ not in before), []
