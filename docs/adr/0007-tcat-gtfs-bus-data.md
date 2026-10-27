# ADR 0007: TCAT bus schedule from the published GTFS feed

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27). Replaces the reserved bus card of [ADR 0006](0006-student-defaults-and-vehicles.md).

## Context

ORS has no transit routing, and a typed bus time (the first design) is not real data. Tompkins Consolidated Area Transit (TCAT) publishes its timetable as a GTFS feed. The team asked for the bus to be built on the real lines, stops, route shapes, directions and which services run on which day.

The feed checked on 2026-10-27 (version 20260922, service 2026-09-22 to 2026-12-19, 1.5 MB): 25 routes, 633 stops, 4,994 trips, 92,332 stop times, 156 shapes. It has one service per weekday group (`calendar.txt`), one date exception (Thanksgiving, no service), no transfers, no frequencies, no real-time feed, and its wheelchair and bike fields are all "unknown". Two facts found by looking at the data matter: `shape_dist_traveled` is in **feet**, and 23,534 stop times run **past 24:00:00** (trips after midnight that belong to the previous service day).

## Decision

- **Data.** `python -m src.update_transit` downloads `https://s3.amazonaws.com/tcat-gtfs/tcat-ny-us.zip`, checks it (size limits, required files, a unit that matches the geometry) and builds one SQLite file in `data/tcat/` (C.3, `gtfs_store.py`). The zip is only read, never extracted or run. A failed build leaves the previous index untouched.
- **Not committed.** `data/` is git-ignored: no licence or terms of use for redistributing the feed were found, so the raw feed and the index stay on each machine. Without them the bus card says the data is not installed and the rest of the app works.
- **Distance unit** is detected by comparing `shape_dist_traveled` with the drawn line length, not assumed.
- **Service days.** A date is active when `calendar.txt` says so for its weekday and period, then `calendar_dates.txt` adds or removes services. A search also looks at the previous service day for trips whose times pass 24:00.
- **Planner** (C.2, `bus_planner.py`). Direct rides only. Candidate stops are the 6 nearest within 900 m at each end. The Commuter walks at 4.5 km/h over a street distance of 1.25 times the straight line and must be at the stop a minute early. The best ride is the one that **arrives first**. The time shown is door to door (walk, wait, ride, walk). The ride distance comes from the feed's own shape distances.
- **No bus is explained**: data not installed, date outside the feed, no stop within reach, no direct route, no service that day (with the routes that do link the places and the next bus), or no more buses that day.
- **Plan and map.** The bus is one more compared way with its own card (route number and colour, headsign, board and alight stops, times, when to leave, next departures). The map draws the ride in the route's colour with its two stops. A new "Leaving" date and time field drives it; the default is now in Ithaca time.
- **Bus emissions** use the placeholder factor (105 g CO2e per km) on the ride distance.

## Consequences

- The schedule is a timetable. A late or cancelled bus is not known, and the page says so.
- **Transfers are not planned.** Many trips need one; the card then says no single route links the places.
- Walking legs use straight lines times 1.25, not routed walks.
- The feed ends on 2026-12-19. After that the page asks for an update (`python -m src.update_transit`). Cornell breaks and holidays follow the feed, which is why a refresh is needed when TCAT publishes a new one.
- Wheelchair and bike-on-bus information is not available (all "unknown" in the feed), so the page does not claim either.
- Real-time positions exist as separate GTFS-realtime feeds listed by Transitland; they were not used.
- **SPEC.md requirement 2.1.11 and model 10.9** still describe a bus time typed by the Commuter, and the model has no transit data source. The team should update both; this ADR does not.
- Needs a new external system in the model (the TCAT schedule) and a C.3 responsibility for the index.
- Tests use an invented feed with the same quirks (feet, past-24:00 times, weekday and weekend services, a date exception, a no-drop-off stop) so they do not depend on the real data; a few extra tests run on the real feed only when it has been built.
- `tzdata` is added for Windows; without it a US daylight-saving rule is used.

## Evidence that would change this decision

- TCAT states terms that allow or forbid committing the feed.
- Real-time data is wanted: add the GTFS-realtime feed.
- Transfers matter to the pilot students: plan one change.
- A reviewed bus emission factor, ideally per passenger, replaces the placeholder.
