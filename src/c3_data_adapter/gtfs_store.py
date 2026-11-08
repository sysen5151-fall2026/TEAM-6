"""Local index of a GTFS transit feed (TCAT, Ithaca) for C.3.

`build_database` turns the agency's GTFS zip into one SQLite file; `GtfsStore` answers the
few questions the bus planner asks (stops near a point, which services run on a date,
which trips link two stop sets, the line a trip follows between two stops). The feed is
read member by member from the zip and never extracted or executed.

Facts about the TCAT feed this was checked against (2026-09-22 version):
- stop times run past 24:00:00 for trips after midnight that belong to the previous service day;
- `shape_dist_traveled` is in FEET, so the unit is detected from the geometry, not assumed;
- one service per weekday (calendar.txt) plus a few exceptions (calendar_dates.txt);
- wheelchair and bike fields are all 0 (unknown), and there are no transfers or frequencies.
"""

import csv
import io
import math
import os
import re
import sqlite3
import statistics
import tempfile
import threading
import zipfile
from pathlib import Path

FEED_URL = "https://s3.amazonaws.com/tcat-gtfs/tcat-ny-us.zip"
ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("TCAT_DB", ROOT / "data" / "tcat" / "tcat.sqlite"))
MAX_UNZIPPED_BYTES = 200 * 1024 * 1024  # refuse a feed that expands to more than this
SCHEMA_VERSION = 1
DEFAULT_COLOR = "2b3a30"
DEFAULT_TEXT = "ffffff"

_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
_UNITS_M = {"metres": 1.0, "feet": 0.3048, "kilometres": 1000.0, "miles": 1609.344}
REQUIRED_FILES = ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "shapes.txt", "calendar.txt")

SCHEMA = """
CREATE TABLE feed (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE stops (stop_id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);
CREATE TABLE routes (route_id TEXT PRIMARY KEY, short_name TEXT, long_name TEXT, color TEXT, text_color TEXT);
CREATE TABLE trips (trip_id TEXT PRIMARY KEY, route_id TEXT, service_id TEXT, headsign TEXT,
                    direction_id INTEGER, shape_id TEXT);
CREATE TABLE stop_times (trip_id TEXT, seq INTEGER, stop_id TEXT, arr_s INTEGER, dep_s INTEGER,
                         dist_m REAL, pickup INTEGER, dropoff INTEGER);
CREATE TABLE shapes (shape_id TEXT, seq INTEGER, lat REAL, lon REAL, dist_m REAL);
CREATE TABLE calendar (service_id TEXT PRIMARY KEY, mon INTEGER, tue INTEGER, wed INTEGER, thu INTEGER,
                       fri INTEGER, sat INTEGER, sun INTEGER, start_date TEXT, end_date TEXT);
CREATE TABLE calendar_dates (service_id TEXT, date TEXT, type INTEGER);
CREATE INDEX st_stop ON stop_times (stop_id);
CREATE INDEX st_trip ON stop_times (trip_id, seq);
CREATE INDEX trip_service ON trips (service_id, route_id);
CREATE INDEX shape_pt ON shapes (shape_id, seq);
"""


class FeedError(ValueError):
    """The zip is not a usable GTFS feed."""


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(h))


def parse_time(text: str):
    """'08:05:30' -> seconds; hours may pass 24 (after midnight on the same service day). None if bad."""
    parts = (text or "").strip().split(":")
    if len(parts) != 3:
        return None
    try:
        h, m, s = (int(p) for p in parts)
    except ValueError:
        return None
    return h * 3600 + m * 60 + s if h >= 0 and 0 <= m < 60 and 0 <= s < 60 else None


def _color(value: str, default: str) -> str:
    value = (value or "").strip().lstrip("#")
    return value.lower() if _HEX.match(value) else default


def _rows(archive: zipfile.ZipFile, name: str):
    """Rows of one file in the zip as dicts; empty when the (optional) file is absent."""
    if name not in archive.namelist():
        return
    with archive.open(name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))


def _detect_unit(shape_points: dict) -> float:
    """Metres per unit of shape_dist_traveled, from how long the drawn lines are."""
    ratios = []
    for points in shape_points.values():
        if len(points) < 2 or points[-1][2] <= 0:
            continue
        length = sum(_haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(points, points[1:]))
        if length > 200:
            ratios.append(points[-1][2] / length)
    if not ratios:
        raise FeedError("Cannot tell the distance unit: no usable shapes with shape_dist_traveled.")
    ratio = statistics.median(ratios)
    best = min(_UNITS_M.items(), key=lambda kv: abs(math.log(ratio * kv[1])))
    if abs(math.log(ratio * best[1])) > math.log(1.2):  # more than 20% off every known unit
        raise FeedError(f"Unrecognised shape_dist_traveled unit (ratio to line length {ratio:.3f}).")
    return best[1]


def build_database(zip_path, db_path=None) -> dict:
    """Read the GTFS zip and write the SQLite index atomically. Returns counts and feed facts."""
    zip_path = Path(zip_path)
    db_path = Path(db_path or DB_PATH)
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as err:
        raise FeedError(f"Not a readable zip file: {err}") from err
    with archive:
        if sum(i.file_size for i in archive.infolist()) > MAX_UNZIPPED_BYTES:
            raise FeedError("The feed expands to more than 200 MB; refusing it.")
        missing = [n for n in REQUIRED_FILES if n not in archive.namelist()]
        if missing:
            raise FeedError("Missing required GTFS files: " + ", ".join(missing))

        shapes = {}
        for r in _rows(archive, "shapes.txt"):
            try:
                shapes.setdefault(r["shape_id"], []).append(
                    (float(r["shape_pt_lat"]), float(r["shape_pt_lon"]), float(r["shape_dist_traveled"]),
                     int(r["shape_pt_sequence"]))
                )
            except (KeyError, ValueError):
                continue
        for points in shapes.values():
            points.sort(key=lambda p: p[3])
        unit_m = _detect_unit(shapes)

        db_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(suffix=".sqlite", dir=db_path.parent)
        os.close(handle)
        tmp = Path(tmp_name)
        con = sqlite3.connect(tmp)
        try:
            con.executescript(SCHEMA)
            skipped = {"stop_times": 0, "trips": 0}

            con.executemany("INSERT OR REPLACE INTO stops VALUES (?,?,?,?)", (
                (r["stop_id"], r.get("stop_name", ""), float(r["stop_lat"]), float(r["stop_lon"]))
                for r in _rows(archive, "stops.txt") if r.get("stop_lat") and r.get("stop_lon")))
            con.executemany("INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?)", (
                (r["route_id"], (r.get("route_short_name") or r["route_id"]).strip(),
                 (r.get("route_long_name") or "").strip(),
                 _color(r.get("route_color"), DEFAULT_COLOR), _color(r.get("route_text_color"), DEFAULT_TEXT))
                for r in _rows(archive, "routes.txt")))

            trips = []
            for r in _rows(archive, "trips.txt"):
                try:
                    trips.append((r["trip_id"], r["route_id"], r["service_id"], (r.get("trip_headsign") or "").strip(),
                                  int(r["direction_id"]) if r.get("direction_id") else -1, r.get("shape_id", "")))
                except KeyError:
                    skipped["trips"] += 1
            con.executemany("INSERT OR REPLACE INTO trips VALUES (?,?,?,?,?,?)", trips)

            batch = []
            for r in _rows(archive, "stop_times.txt"):
                arr, dep = parse_time(r.get("arrival_time")), parse_time(r.get("departure_time"))
                arr = dep if arr is None else arr
                dep = arr if dep is None else dep
                if arr is None:
                    skipped["stop_times"] += 1
                    continue
                try:
                    dist = float(r["shape_dist_traveled"]) * unit_m
                    batch.append((r["trip_id"], int(r["stop_sequence"]), r["stop_id"], arr, dep, dist,
                                  int(r.get("pickup_type") or 0), int(r.get("drop_off_type") or 0)))
                except (KeyError, ValueError, TypeError):
                    skipped["stop_times"] += 1
                    continue
                if len(batch) >= 20000:
                    con.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?,?,?)", batch)
                    batch = []
            con.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?,?,?)", batch)

            con.executemany("INSERT INTO shapes VALUES (?,?,?,?,?)", (
                (sid, p[3], p[0], p[1], p[2] * unit_m) for sid, pts in shapes.items() for p in pts))
            con.executemany("INSERT OR REPLACE INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?)", (
                (r["service_id"], *(int(r[d]) for d in ("monday", "tuesday", "wednesday", "thursday", "friday",
                                                         "saturday", "sunday")), r["start_date"], r["end_date"])
                for r in _rows(archive, "calendar.txt")))
            con.executemany("INSERT INTO calendar_dates VALUES (?,?,?)", (
                (r["service_id"], r["date"], int(r["exception_type"])) for r in _rows(archive, "calendar_dates.txt")))

            info = next(iter(_rows(archive, "feed_info.txt")), {})
            agency = next(iter(_rows(archive, "agency.txt")), {})
            feed = {
                "schema": str(SCHEMA_VERSION),
                "agency": agency.get("agency_name", ""),
                "timezone": agency.get("agency_timezone", "America/New_York"),
                "version": info.get("feed_version", ""),
                "start_date": info.get("feed_start_date") or min((r[0] for r in con.execute("SELECT start_date FROM calendar")), default=""),
                "end_date": info.get("feed_end_date") or max((r[0] for r in con.execute("SELECT end_date FROM calendar")), default=""),
                "distance_unit_m": str(unit_m),
                "source": FEED_URL,
            }
            con.executemany("INSERT INTO feed VALUES (?,?)", feed.items())
            counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                      for t in ("stops", "routes", "trips", "stop_times", "shapes", "calendar", "calendar_dates")}
            con.commit()
        except Exception:
            con.close()
            tmp.unlink(missing_ok=True)
            raise
        con.close()
    os.replace(tmp, db_path)
    return {"feed": feed, "counts": counts, "skipped": skipped, "unit_m": unit_m}


class GtfsStore:
    """Read-only questions over the SQLite index."""

    def __init__(self, path):
        self.path = Path(path)
        self._local = threading.local()  # one read-only connection per thread (the web server is threaded)
        self._feed = {r["key"]: r["value"] for r in self.con.execute("SELECT key, value FROM feed")}
        if self._feed.get("schema") != str(SCHEMA_VERSION):
            raise FeedError("The transit index was built by a different version; run the update again.")

    @property
    def con(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            self._local.con = con
        return con

    def feed_info(self) -> dict:
        return dict(self._feed)

    def covers(self, day: str) -> bool:
        """day is YYYYMMDD."""
        return self._feed["start_date"] <= day <= self._feed["end_date"]

    def stops_near(self, lat: float, lon: float, radius_m: float, limit: int) -> list:
        dlat = radius_m / 111320.0
        dlon = radius_m / (111320.0 * max(math.cos(math.radians(lat)), 0.01))
        rows = self.con.execute(
            "SELECT stop_id, name, lat, lon FROM stops WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
            (lat - dlat, lat + dlat, lon - dlon, lon + dlon)).fetchall()
        found = [(_haversine_m(lat, lon, r["lat"], r["lon"]), dict(r)) for r in rows]
        found = [(d, s) for d, s in found if d <= radius_m]
        found.sort(key=lambda x: (x[0], x[1]["stop_id"]))
        return [dict(s, straight_m=d) for d, s in found[:limit]]

    def active_services(self, day: str, weekday: int) -> set:
        """Service ids that run on `day` (YYYYMMDD; weekday 0=Monday): calendar rows plus date exceptions."""
        col = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[weekday]
        services = {r[0] for r in self.con.execute(
            f"SELECT service_id FROM calendar WHERE {col} = 1 AND start_date <= ? AND end_date >= ?", (day, day))}
        for service_id, kind in self.con.execute("SELECT service_id, type FROM calendar_dates WHERE date = ?", (day,)):
            (services.add if kind == 1 else services.discard)(service_id)
        return services

    def departures(self, board_ids, alight_ids, service_ids, from_s: int, limit: int = 80) -> list:
        """Trips that call at one of `board_ids` and later at one of `alight_ids`, leaving at or after from_s."""
        board_ids, alight_ids, service_ids = list(board_ids), list(alight_ids), list(service_ids)
        if not (board_ids and alight_ids and service_ids):
            return []
        marks = lambda items: ",".join("?" * len(items))  # noqa: E731
        sql = f"""
            SELECT a.trip_id, a.stop_id AS board_stop, a.dep_s, a.dist_m AS board_dist,
                   b.stop_id AS alight_stop, b.arr_s, b.dist_m AS alight_dist,
                   t.route_id, t.headsign, t.direction_id, t.shape_id, t.service_id
            FROM stop_times a
            JOIN stop_times b ON b.trip_id = a.trip_id AND b.seq > a.seq
            JOIN trips t ON t.trip_id = a.trip_id
            WHERE a.stop_id IN ({marks(board_ids)}) AND b.stop_id IN ({marks(alight_ids)})
              AND t.service_id IN ({marks(service_ids)}) AND a.dep_s >= ?
              AND a.pickup <> 1 AND b.dropoff <> 1
            ORDER BY a.dep_s, a.trip_id LIMIT ?"""
        rows = self.con.execute(sql, (*board_ids, *alight_ids, *service_ids, from_s, limit)).fetchall()
        return [dict(r) for r in rows]

    def routes_connecting(self, board_ids, alight_ids) -> list:
        """Routes (any day) with a trip from one stop set to the other: [(route_id, short_name, [service ids])]."""
        board_ids, alight_ids = list(board_ids), list(alight_ids)
        if not (board_ids and alight_ids):
            return []
        marks = lambda items: ",".join("?" * len(items))  # noqa: E731
        rows = self.con.execute(f"""
            SELECT DISTINCT t.route_id, r.short_name, t.service_id
            FROM stop_times a JOIN stop_times b ON b.trip_id = a.trip_id AND b.seq > a.seq
            JOIN trips t ON t.trip_id = a.trip_id JOIN routes r ON r.route_id = t.route_id
            WHERE a.stop_id IN ({marks(board_ids)}) AND b.stop_id IN ({marks(alight_ids)})
              AND a.pickup <> 1 AND b.dropoff <> 1""", (*board_ids, *alight_ids)).fetchall()
        grouped = {}
        for r in rows:
            grouped.setdefault((r["route_id"], r["short_name"]), []).append(r["service_id"])
        return [(rid, name, sorted(services)) for (rid, name), services in sorted(grouped.items())]

    def route(self, route_id: str) -> dict:
        row = self.con.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,)).fetchone()
        return dict(row) if row else {"route_id": route_id, "short_name": route_id, "long_name": "",
                                      "color": DEFAULT_COLOR, "text_color": DEFAULT_TEXT}

    def stop(self, stop_id: str) -> dict:
        row = self.con.execute("SELECT * FROM stops WHERE stop_id = ?", (stop_id,)).fetchone()
        return dict(row) if row else {}

    def shape_between(self, shape_id: str, from_m: float, to_m: float) -> list:
        """(lat, lon) points of the shape between two distances along it, both ends included."""
        rows = self.con.execute(
            "SELECT lat, lon, dist_m FROM shapes WHERE shape_id = ? ORDER BY seq", (shape_id,)).fetchall()
        return [(r["lat"], r["lon"]) for r in rows if from_m <= r["dist_m"] <= to_m]


_cache = {}  # (path, modified time) -> GtfsStore


def open_store(path=None):
    """The transit index, or None when it has not been built (or cannot be read)."""
    path = Path(path or DB_PATH)
    try:
        key = (str(path), path.stat().st_mtime_ns)
    except OSError:
        return None
    if key not in _cache:
        try:
            _cache.clear()
            _cache[key] = GtfsStore(path)
        except (FeedError, sqlite3.Error, KeyError):
            return None
    return _cache[key]
