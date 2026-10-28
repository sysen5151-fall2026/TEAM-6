"""Find a direct TCAT bus between two places from the published schedule.

Rules (the numbers are PROJECT ASSUMPTIONS, not measurements):
- The Commuter walks to a stop at most MAX_WALK_M away, at WALK_SPEED_MPS, over a street
  distance taken as WALK_DETOUR times the straight line.
- Only direct rides are planned; transfers are not (the feed has no transfer rules).
- The schedule is the timetable, not live bus positions: a late bus is not known.
- A trip after midnight belongs to the previous service day, so both days are searched.
Times are local to Ithaca (America/New_York).
"""

from datetime import datetime, timedelta, timezone

from src.c3_data_adapter import open_store
from src.interfaces import BusItinerary, BusResult, BusStop, Place
from src.model_trace import realizes

MAX_WALK_M = 900.0  # about a 12 minute walk
NEAR_STOPS = 6  # candidate stops at each end
WALK_SPEED_MPS = 1.25  # 4.5 km/h
WALK_DETOUR = 1.25  # street distance over straight line
SLACK_S = 60  # be at the stop a minute before the bus
LOOKAHEAD_DAYS = 7  # how far to look for the next bus when there is none on the day
NEXT_SHOWN = 3
MAX_OPTIONS = 5  # routes offered when several link the same two places
OPTION_WINDOW_S = 3600  # an alternative must arrive within an hour of the best (a night-only route is not one)
DEPARTURES_LOOKED_AT = 400  # enough that a route with few trips is not crowded out by a busy one
DAY = 86400
UPDATE_HINT = "python -m src.update_transit"


# ------------------------------------------------------------------ local time
def _us_eastern_offset_hours(utc: datetime) -> int:
    """Used only when the time zone database is missing (Windows without tzdata)."""
    march = datetime(utc.year, 3, 8, 7)  # 02:00 EST on the second Sunday of March
    start = march + timedelta(days=(6 - march.weekday()) % 7)
    november = datetime(utc.year, 11, 1, 6)  # 02:00 EDT on the first Sunday of November
    end = november + timedelta(days=(6 - november.weekday()) % 7)
    return -4 if start <= utc < end else -5


def local_now() -> datetime:
    """Now in Ithaca as a naive datetime (no zone attached), to the minute."""
    try:
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    except Exception:  # noqa: BLE001 - ZoneInfoNotFoundError and friends: fall back to the US rule
        utc = datetime.now(timezone.utc).replace(tzinfo=None)
        now = utc + timedelta(hours=_us_eastern_offset_hours(utc))
    return now.replace(second=0, microsecond=0)


# ------------------------------------------------------------------ helpers
def _clock(seconds: float) -> str:
    seconds = int(seconds)
    return f"{(seconds // 3600) % 24:02d}:{(seconds % 3600) // 60:02d}"


def _gtfs_date(day) -> str:
    return day.strftime("%Y%m%d")


def _pretty_date(yyyymmdd: str) -> str:
    return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%a %b %d").replace(" 0", " ")


def _minutes(seconds: float) -> int:
    return max(0, round(seconds / 60))


def _stop(row: dict) -> BusStop:
    return BusStop(row["stop_id"], row["name"], row["lat"], row["lon"])


def _build(store, row, board, alight, day, offset, walk_to_s, walk_from_s, tod_s, same_route_times):
    """One BusItinerary from a departures row; times are seconds since midnight of `day`."""
    dep = row["dep_s"] - offset
    arr = row["arr_s"] - offset
    route = store.route(row["route_id"])
    stop_from, stop_to = store.stop(row["board_stop"]), store.stop(row["alight_stop"])
    shape = store.shape_between(row["shape_id"], row["board_dist"], row["alight_dist"])
    path = ((stop_from["lat"], stop_from["lon"]), *shape, (stop_to["lat"], stop_to["lon"]))
    reach_s = arr + walk_from_s
    return BusItinerary(
        route_id=row["route_id"],
        route_name=route["short_name"],
        color=route["color"],
        text_color=route["text_color"],
        headsign=row["headsign"],
        direction_id=row["direction_id"],
        board=_stop(stop_from),
        alight=_stop(stop_to),
        leave_time=_clock(dep - walk_to_s),
        depart_time=_clock(dep),
        arrive_time=_clock(arr),
        arrive_destination=_clock(reach_s),
        walk_to_m=round(board["straight_m"] * WALK_DETOUR),
        walk_from_m=round(alight["straight_m"] * WALK_DETOUR),
        walk_to_min=_minutes(walk_to_s),
        walk_from_min=_minutes(walk_from_s),
        wait_min=_minutes(dep - (tod_s + walk_to_s)),
        ride_min=_minutes(arr - dep),
        ride_km=round((row["alight_dist"] - row["board_dist"]) / 1000, 2),
        total_min=_minutes(reach_s - tod_s),
        service_date=day.isoformat(),
        next_departures=tuple(_clock(t) for t in same_route_times[:NEXT_SHOWN]),
        path=path,
        feed_version=store.feed_info().get("version", ""),
    )


def _options_on_day(store, day, tod_s, boards, alights) -> list:
    """The best direct ride of each route that leaves on `day` at or after tod_s (seconds).

    One ride per route (the one that arrives first), earliest arrival first, at most MAX_OPTIONS,
    and only those that arrive within OPTION_WINDOW_S of the best one.
    """
    walk_in = {b["stop_id"]: b["straight_m"] * WALK_DETOUR / WALK_SPEED_MPS for b in boards}
    walk_out = {a["stop_id"]: a["straight_m"] * WALK_DETOUR / WALK_SPEED_MPS for a in alights}
    by_board = {b["stop_id"]: b for b in boards}
    by_alight = {a["stop_id"]: a for a in alights}
    candidates = []
    # service day `day` itself, and the previous service day's trips that run past midnight
    for service_day, offset in ((day, 0), (day - timedelta(days=1), DAY)):
        services = store.active_services(_gtfs_date(service_day), service_day.weekday())
        rows = store.departures(by_board, by_alight, services, tod_s + offset, limit=DEPARTURES_LOOKED_AT)
        for r in rows:
            dep = r["dep_s"] - offset
            if dep < tod_s + walk_in[r["board_stop"]] + SLACK_S:
                continue  # cannot reach this stop in time
            reach = r["arr_s"] - offset + walk_out[r["alight_stop"]]
            candidates.append((reach, dep, r, offset))
    best = {}
    for c in sorted(candidates, key=lambda c: (c[0], c[1], c[2]["trip_id"])):
        best.setdefault(c[2]["route_id"], c)
    ordered = sorted(best.values(), key=lambda c: (c[0], c[1], c[2]["route_id"]))
    # only routes that are a real alternative: not one that gets there more than an hour after the best
    chosen = [c for c in ordered if ordered and c[0] <= ordered[0][0] + OPTION_WINDOW_S][:MAX_OPTIONS]
    options = []
    for reach, dep, row, offset in chosen:
        same = sorted({c[1] for c in candidates
                       if c[2]["route_id"] == row["route_id"] and c[2]["board_stop"] == row["board_stop"] and c[1] > dep})
        options.append(_build(store, row, by_board[row["board_stop"]], by_alight[row["alight_stop"]], day, offset,
                              walk_in[row["board_stop"]], walk_out[row["alight_stop"]], tod_s, same))
    return options


def _best_on_day(store, day, tod_s, boards, alights):
    """Earliest-arriving direct ride that leaves on `day` at or after tod_s (seconds), else None."""
    options = _options_on_day(store, day, tod_s, boards, alights)
    return options[0] if options else None


@realizes("UC.3.4")
def find_bus(origin: Place, dest: Place, when: datetime, store=None) -> BusResult:
    """The direct buses for leaving `origin` at `when` (one ride per route, best first), or the reason there is none."""
    store = store or open_store()
    if store is None:
        return BusResult(None, "not_installed", f"Bus times are not installed yet. Run: {UPDATE_HINT}")

    day = when.date()
    info = store.feed_info()
    if not store.covers(_gtfs_date(day)):
        return BusResult(None, "outside_feed",
                         f"The TCAT schedule we have covers {_pretty_date(info['start_date'])} to "
                         f"{_pretty_date(info['end_date'])}, not {_pretty_date(_gtfs_date(day))}. "
                         f"Update it with: {UPDATE_HINT}")

    boards = store.stops_near(origin.lat, origin.lon, MAX_WALK_M, NEAR_STOPS)
    alights = store.stops_near(dest.lat, dest.lon, MAX_WALK_M, NEAR_STOPS)
    if not boards:
        return BusResult(None, "no_stop_near_start", f"No TCAT stop within {MAX_WALK_M:g} m of the start.")
    if not alights:
        return BusResult(None, "no_stop_near_destination", f"No TCAT stop within {MAX_WALK_M:g} m of the destination.")

    connecting = store.routes_connecting([b["stop_id"] for b in boards], [a["stop_id"] for a in alights])
    if not connecting:
        return BusResult(None, "no_direct_route",
                         "No single TCAT route links the stops near these two places (transfers are not planned yet).")

    tod_s = when.hour * 3600 + when.minute * 60
    options = _options_on_day(store, day, tod_s, boards, alights)
    if options:
        return BusResult(options[0], "ok", "", None, tuple(options))

    # Nothing on that day at that time: say why, and find the next bus.
    active = store.active_services(_gtfs_date(day), day.weekday())
    runs_that_day = any(set(services) & active for _, _, services in connecting)
    later = None
    for ahead in range(1, LOOKAHEAD_DAYS + 1):
        later_day = day + timedelta(days=ahead)
        if not store.covers(_gtfs_date(later_day)):
            break
        later = _best_on_day(store, later_day, 0, boards, alights)
        if later:
            break
    when_next = ""
    if later:
        d = datetime.fromisoformat(later.service_date)
        when_next = f" The next one is route {later.route_name} on {d.strftime('%a %b %d').replace(' 0', ' ')} at {later.depart_time}."
    if not active:
        return BusResult(None, "no_service_that_day",
                         f"TCAT has no scheduled service on {_pretty_date(_gtfs_date(day))}.{when_next}", later)
    if not runs_that_day:
        names = sorted({n for _, n, _ in connecting}, key=lambda x: (len(x), x))
        shown = ", ".join(names[:6]) + (" and more" if len(names) > 6 else "")
        return BusResult(None, "no_service_that_day",
                         f"No TCAT route between these places runs on {_pretty_date(_gtfs_date(day))} "
                         f"(routes that link them run on other days: {shown}).{when_next}", later)
    return BusResult(None, "no_more_that_day",
                     f"No more TCAT buses between these places after {_clock(tod_s)} on {_pretty_date(_gtfs_date(day))}."
                     f"{when_next}", later)
