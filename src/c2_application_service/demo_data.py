"""Sample confirmed trips so a demonstration can show badges and the campus tree.

They stop just short of some goals on purpose, so confirming one more real trip can earn a badge.

These are invented sample records, loaded only when the Commuter asks, and the page says so.
"""

from src.c3_data_adapter import add_confirmed, retrieve_factor
from src.interfaces import CommuteRequest, ConfirmedTrip

# (date, mode, destination, distance_km, recommended_mode)
_SAMPLE = (
    ("2026-10-05", "drive", "Cornell Arts Quad", 4.2, "bike"),
    ("2026-10-06", "bike", "Cornell Arts Quad", 4.2, "bike"),
    ("2026-10-07", "bus", "Cornell Gates Hall", 4.4, "bike"),
    ("2026-10-08", "bike", "Cornell Gates Hall", 4.4, "bike"),
    ("2026-10-12", "walk", "Ithaca Commons", 3.1, "walk"),
    ("2026-10-13", "bike", "Collegetown", 3.0, "bike"),
    ("2026-10-14", "bike", "Cornell Arts Quad", 4.2, "bus"),
    ("2026-10-15", "bus", "Olin Library", 4.6, "bike"),
    ("2026-10-19", "bike", "Cornell Arts Quad", 4.2, "bus"),
    ("2026-10-20", "bike", "Statler Hall", 4.5, "bus"),
    ("2026-10-21", "walk", "Collegetown", 3.0, "bike"),
    ("2026-10-22", "bike", "Cornell Gates Hall", 4.4, "walk"),
)
ORIGIN = "Home (sample)"


def _g(mode: str, km: float) -> float:
    request = CommuteRequest(mode=mode, distance_km=1.0, date="", coarse_area="")
    return round(km * retrieve_factor(request).g_co2e_per_km)


def load_demo_trips() -> int:
    """Add the sample trips; returns how many were new."""
    added = 0
    for day, mode, destination, km, recommended in _SAMPLE:
        co2e = _g(mode, km)
        trip = ConfirmedTrip(day, mode, ORIGIN, destination, km, co2e, _g("drive", km) - co2e, recommended)
        added += add_confirmed(trip)
    return added
