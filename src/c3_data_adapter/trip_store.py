"""Stores of the trips a Commuter confirmed.

`MemoryTrips` keeps them for the life of the process (the command-line path, the tests, and
anyone not logged in). `SqliteTrips` keeps one account's trips in the application database, so
they are still there after a restart. Both answer the same four questions: add, all, clear and
(for the database) what the others have done in total.
"""

from src.interfaces import ConfirmedTrip
from src.model_trace import realizes
from src.c3_data_adapter import app_db


def trip_key(trip: ConfirmedTrip) -> tuple:
    """Date, places and way; a drive and a carpool of the same trip are the same car trip."""
    return (trip.date, trip.origin, trip.destination, "drive" if trip.mode == "carpool" else trip.mode)


class MemoryTrips:
    def __init__(self):
        self._trips = []

    def add(self, trip: ConfirmedTrip) -> bool:
        """Store the trip; False when the same date, places and way were already confirmed."""
        if any(trip_key(t) == trip_key(trip) for t in self._trips):
            return False
        self._trips.append(trip)
        return True

    def all(self) -> tuple:
        return tuple(self._trips)

    def clear(self) -> None:
        self._trips.clear()


_COLUMNS = ("date", "mode", "origin", "destination", "distance_km", "co2e_g", "difference_g",
            "recommended_mode", "occupants", "route")


class SqliteTrips:
    """One account's trips in the application database."""

    def __init__(self, db, user_id: int):
        self.db, self.user_id = db, user_id

    def add(self, trip: ConfirmedTrip) -> bool:
        import time

        key = "|".join(str(part) for part in trip_key(trip))
        cursor = self.db.execute(
            f"INSERT OR IGNORE INTO trips (user_id, tkey, {', '.join(_COLUMNS)}, created_at) "
            f"VALUES (?, ?, {', '.join('?' * len(_COLUMNS))}, ?)",
            (self.user_id, key, *(getattr(trip, c) for c in _COLUMNS), int(time.time())))
        return cursor.rowcount == 1

    def all(self) -> tuple:
        rows = self.db.execute(f"SELECT {', '.join(_COLUMNS)} FROM trips WHERE user_id = ? ORDER BY id",
                               (self.user_id,)).fetchall()
        return tuple(ConfirmedTrip(**{c: r[c] for c in _COLUMNS}) for r in rows)

    def clear(self) -> None:
        self.db.execute("DELETE FROM trips WHERE user_id = ?", (self.user_id,))


def other_users_trips(db, user_id: int) -> tuple:
    """Every other account's trips, one tuple per account, for the shared tree total.

    Only these totals are ever shown; no page names another account or lists their trips.
    """
    grouped = {}
    for r in db.execute(f"SELECT user_id, {', '.join(_COLUMNS)} FROM trips WHERE user_id <> ? ORDER BY id", (user_id,)):
        grouped.setdefault(r["user_id"], []).append(ConfirmedTrip(**{c: r[c] for c in _COLUMNS}))
    return tuple(tuple(trips) for trips in grouped.values())


# --- the default store, used when none is given -----------------------------------------------
_DEFAULT = MemoryTrips()


@realizes("UC.3.8")
def add_confirmed(trip: ConfirmedTrip, store=None) -> bool:
    return (store or _DEFAULT).add(trip)


def confirmed_trips(store=None) -> tuple:
    return (store or _DEFAULT).all()


def reset_confirmed(store=None) -> None:
    (store or _DEFAULT).clear()
