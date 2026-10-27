"""A tiny invented GTFS feed that has the quirks of the real TCAT one, for tests.

Quirks copied on purpose: distances in FEET, a trip with times past 24:00, one service per
weekday group, a date exception that removes a weekday and one that adds a Saturday service,
routes that run only on weekdays or only at weekends, and a stop where nobody may get off.

Stops: A1 near the start, B1 about 1.5 km away, C1 further on, E1 on a route that only
links C1 and E1 (so A -> E has no direct bus).
"""

import csv
import io
import math
import tempfile
import zipfile
from pathlib import Path

A, B, C, E = (42.4491, -76.4835), (42.4396, -76.4968), (42.5000, -76.4000), (42.4600, -76.5400)
NEAR_A = (42.4495, -76.4835)  # about 45 m from A1
NEAR_B = (42.4398, -76.4966)
NEAR_E = (42.4601, -76.5401)
FEET_PER_M = 1 / 0.3048

WEDNESDAY, SATURDAY, SUNDAY = "2026-06-03", "2026-06-06", "2026-06-07"
HOLIDAY_FRIDAY = "2026-07-03"  # WK removed, SA added by calendar_dates


def _hav(p, q):
    p1, p2 = math.radians(p[0]), math.radians(q[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(q[1] - p[1]) / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(h))


def _hms(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _csv(header, rows) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def _shape_rows(shape_id, points):
    rows, total = [], 0.0
    for i, pt in enumerate(points):
        if i:
            total += _hav(points[i - 1], pt)
        rows.append((shape_id, pt[0], pt[1], i + 1, round(total * FEET_PER_M, 3)))
    return rows


def _mid(p, q, f=0.5):
    return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)


def feed_files(version="test-1", start="20260101", end="20261231") -> dict:
    stops = {"A1": A, "B1": B, "C1": C, "E1": E}
    shape_abc = [A, _mid(A, B, 0.5), B, _mid(B, C, 0.5), C]
    shape_cba = list(reversed(shape_abc))
    shape_ce = [C, _mid(C, E, 0.5), E]
    shapes = _shape_rows("S_ABC", shape_abc) + _shape_rows("S_CBA", shape_cba) + _shape_rows("S_CE", shape_ce)
    dist_ft = {name: rows[-1][4] for name, rows in (("S_ABC", _shape_rows("S_ABC", shape_abc)),)}
    d_ab = round(sum(_hav(shape_abc[i], shape_abc[i + 1]) for i in range(2)) * FEET_PER_M, 3)
    d_abc = dist_ft["S_ABC"]
    d_ce = _shape_rows("S_CE", shape_ce)[-1][4]

    trips, times = [], []

    def add_trip(trip_id, route, service, headsign, direction, shape, calls):
        """calls: [(stop_id, seconds, shape_dist_ft, pickup, dropoff)]"""
        trips.append((route, service, trip_id, headsign, direction, "", shape, 0, 0))
        for seq, (stop, secs, dist, pickup, dropoff) in enumerate(calls):
            times.append((trip_id, _hms(secs), _hms(secs), stop, seq * 10, "", pickup, dropoff, dist, 1))

    def abc(start_s, trip_id, route="R1", service="WK"):
        add_trip(trip_id, route, service, "Downtown", 0, "S_ABC",
                 [("A1", start_s, 0, 0, 0), ("B1", start_s + 600, d_ab, 0, 0), ("C1", start_s + 1500, d_abc, 0, 0)])

    for k in range(33):  # weekdays: every 30 minutes, 06:00 to 22:00
        abc(6 * 3600 + k * 1800, f"wk{k}")
    for k in range(13):  # Saturday and Sunday: hourly, 08:00 to 20:00
        abc(8 * 3600 + k * 3600, f"sa{k}", service="SA")
        abc(8 * 3600 + k * 3600, f"su{k}", service="SU")
    for k in range(17):  # the other direction, weekdays, hourly
        s = 6 * 3600 + k * 3600
        add_trip(f"back{k}", "R1", "WK", "Campus", 1, "S_CBA",
                 [("C1", s, 0, 0, 0), ("B1", s + 900, d_abc - d_ab, 0, 0), ("A1", s + 1500, d_abc, 0, 0)])
    # a night trip that runs past midnight: it belongs to the weekday service of the day it starts
    abc(23 * 3600 + 50 * 60, "night", route="R2")
    times_night = [t for t in times if t[0] == "night"]
    for i, secs in enumerate((23 * 3600 + 50 * 60, 24 * 3600 + 5 * 60, 24 * 3600 + 20 * 60)):
        old = times_night[i]
        times[times.index(old)] = (old[0], _hms(secs), _hms(secs), old[3], old[4], "", old[6], old[7], old[8], 1)
    # route 65 runs on weekdays only: a slow trip that leaves early, and a fast one that leaves late
    add_trip("r3slow", "R3", "WK", "Downtown", 0, "S_ABC", [("A1", 8 * 3600 + 3300, 0, 0, 0), ("B1", 9 * 3600 + 2400, d_ab, 0, 0), ("C1", 9 * 3600 + 3000, d_abc, 0, 0)])
    add_trip("r3fast", "R3", "WK", "Downtown", 0, "S_ABC", [("A1", 9 * 3600 + 1200, 0, 0, 0), ("B1", 9 * 3600 + 1500, d_ab, 0, 0), ("C1", 9 * 3600 + 2000, d_abc, 0, 0)])
    abc(10 * 3600, "r4sa", route="R4", service="SA")  # weekend-only route
    abc(10 * 3600, "r4su", route="R4", service="SU")
    add_trip("ce", "R5", "WK", "Island", 0, "S_CE", [("C1", 12 * 3600, 0, 0, 0), ("E1", 12 * 3600 + 900, d_ce, 0, 0)])
    # nobody may get off at B1 on this one, though it would arrive there first
    add_trip("nodrop", "R1", "WK", "Downtown", 0, "S_ABC",
             [("A1", 7 * 3600 + 900, 0, 0, 0), ("B1", 7 * 3600 + 1200, d_ab, 0, 1), ("C1", 7 * 3600 + 2100, d_abc, 0, 0)])

    routes = [("R1", "30", "Route 30", "AB6339", "FFFFFF"), ("R2", "90", "Night", "014964", "FFFFFF"),
              ("R3", "65", "Weekday", "bad color", "FFFFFF"), ("R4", "115", "Weekend", "", ""),
              ("R5", "51", "Island", "00FF00", "000000")]
    return {
        "agency.txt": _csv(["agency_id", "agency_name", "agency_url", "agency_timezone"],
                           [("0", "Test Transit", "http://example.test/", "America/New_York")]),
        "feed_info.txt": _csv(["feed_publisher_name", "feed_version", "feed_start_date", "feed_end_date"],
                              [("Test", version, start, end)]),
        "stops.txt": _csv(["stop_id", "stop_name", "stop_lat", "stop_lon"],
                          [(sid, f"Stop {sid}", lat, lon) for sid, (lat, lon) in stops.items()]),
        "routes.txt": _csv(["route_id", "route_short_name", "route_long_name", "route_color", "route_text_color"], routes),
        "trips.txt": _csv(["route_id", "service_id", "trip_id", "trip_headsign", "direction_id", "block_id", "shape_id",
                           "wheelchair_accessible", "bikes_allowed"], trips),
        "stop_times.txt": _csv(["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "stop_headsign",
                                "pickup_type", "drop_off_type", "shape_dist_traveled", "timepoint"], times),
        "shapes.txt": _csv(["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"], shapes),
        "calendar.txt": _csv(["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                              "start_date", "end_date"],
                             [("WK", 1, 1, 1, 1, 1, 0, 0, start, end), ("SA", 0, 0, 0, 0, 0, 1, 0, start, end),
                              ("SU", 0, 0, 0, 0, 0, 0, 1, start, end)]),
        "calendar_dates.txt": _csv(["service_id", "date", "exception_type"],
                                   [("WK", "20260703", 2), ("SA", "20260703", 1)]),
    }


def write_zip(path, files=None, drop=()):
    files = feed_files() if files is None else files
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            if name not in drop:
                z.writestr(name, text)
    return Path(path)


def build_fixture_store(folder=None, **kw):
    """Build the invented feed into an index and open it: (store, zip path, db path)."""
    from src.c3_data_adapter.gtfs_store import GtfsStore, build_database

    folder = Path(folder or tempfile.mkdtemp())
    zip_path = write_zip(folder / "feed.zip", feed_files(**kw))
    db_path = folder / "index.sqlite"
    build_database(zip_path, db_path)
    return GtfsStore(db_path), zip_path, db_path
