"""In-memory store of trips the Commuter confirmed (STUB, like the C.3 trip store).

Holds one demo Commuter's trips; everything resets when the server restarts.
"""

from src.interfaces import ConfirmedTrip
from src.model_trace import realizes

_CONFIRMED = []


def trip_key(trip: ConfirmedTrip) -> tuple:
    """Date, places and way; a drive and a carpool of the same trip are the same car trip."""
    return (trip.date, trip.origin, trip.destination, "drive" if trip.mode == "carpool" else trip.mode)


@realizes("UC.3.8")
def add_confirmed(trip: ConfirmedTrip) -> bool:
    """Store the trip; False when the same date, places and way were already confirmed."""
    if any(trip_key(t) == trip_key(trip) for t in _CONFIRMED):
        return False
    _CONFIRMED.append(trip)
    return True


def confirmed_trips() -> tuple:
    return tuple(_CONFIRMED)


def reset_confirmed() -> None:
    _CONFIRMED.clear()
