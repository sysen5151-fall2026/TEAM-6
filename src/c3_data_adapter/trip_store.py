"""In-memory store of trips the Commuter confirmed (STUB, like the C.3 trip store).

Holds one demo Commuter's trips; everything resets when the server restarts.
"""

from src.interfaces import ConfirmedTrip
from src.model_trace import realizes

_CONFIRMED = []


@realizes("UC.3.8")
def add_confirmed(trip: ConfirmedTrip) -> bool:
    """Store the trip; False when the same date, places and mode were already confirmed."""
    key = (trip.date, trip.origin, trip.destination, trip.mode)
    if any((t.date, t.origin, t.destination, t.mode) == key for t in _CONFIRMED):
        return False
    _CONFIRMED.append(trip)
    return True


def confirmed_trips() -> tuple:
    return tuple(_CONFIRMED)


def reset_confirmed() -> None:
    _CONFIRMED.clear()
