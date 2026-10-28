"""TCAT-style transit data: import, service days, trip finding and the bus in the plan.

These use the invented feed in tests/gtfs_fixture.py, never the real data or the network.
A last class runs against the real feed only when it has been built on this machine.

Run:  python -m unittest discover -s tests -t .
"""

import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from src.c2_application_service import bus_planner, plan_commute
from src.c2_application_service.bus_planner import find_bus, local_now
from src.c3_data_adapter import gtfs_store
from src.c3_data_adapter.gtfs_store import FeedError, GtfsStore, build_database, parse_time
from src.interfaces import Place, WeatherForecast

from tests import gtfs_fixture as fx

DRY = WeatherForecast(precipitation_mm=0.0, forecast_timestamp="t", temperature_c=15.0, wind_kmh=5.0)


def place(name, pt):
    return Place(name, pt[1], pt[0], "test")


START, END = place("Start", fx.NEAR_A), place("End", fx.NEAR_B)


def at(day, hhmm):
    return datetime.fromisoformat(f"{day}T{hhmm}")


class TestParseTime(unittest.TestCase):
    def test_hours_may_pass_24_for_trips_after_midnight(self):
        self.assertEqual(parse_time("08:05:30"), 8 * 3600 + 5 * 60 + 30)
        self.assertEqual(parse_time("24:05:00"), 24 * 3600 + 300)
        self.assertEqual(parse_time(" 7:00:00 "), 7 * 3600)

    def test_bad_values_are_none(self):
        for bad in ("", None, "8:05", "aa:bb:cc", "08:61:00", "08:00:99", "-1:00:00"):
            with self.subTest(bad=bad):
                self.assertIsNone(parse_time(bad))


class TestBuild(unittest.TestCase):
    def test_counts_and_feet_are_detected_from_the_geometry(self):
        folder = Path(tempfile.mkdtemp())
        zp = fx.write_zip(folder / "feed.zip")
        result = build_database(zp, folder / "i.sqlite")
        self.assertAlmostEqual(result["unit_m"], 0.3048)
        self.assertEqual(result["counts"]["stops"], 4)
        self.assertEqual(result["counts"]["routes"], 5)
        self.assertEqual(result["skipped"], {"stop_times": 0, "trips": 0})

    def test_distances_are_stored_in_metres(self):
        store, _, _ = fx.build_fixture_store()
        row = store.departures(["A1"], ["B1"], ["WK"], 6 * 3600, limit=1)[0]
        ride_m = row["alight_dist"] - row["board_dist"]
        self.assertTrue(1300 < ride_m < 1700, ride_m)  # A to B is about 1.5 km, not 5,000 ft read as metres

    def test_metres_and_kilometres_feeds_are_detected_too(self):
        for unit in (0.3048, 1.0, 1000.0):
            with self.subTest(unit_m=unit):
                files = fx.feed_files()
                lines = files["shapes.txt"].splitlines()
                # the invented shapes are in feet; restate every distance in the unit under test
                body = [",".join(r.split(",")[:4] + [str(float(r.split(",")[4]) * 0.3048 / unit)]) for r in lines[1:]]
                files["shapes.txt"] = chr(10).join([lines[0]] + body) + chr(10)
                folder = Path(tempfile.mkdtemp())
                fx.write_zip(folder / "f.zip", files)
                self.assertAlmostEqual(build_database(folder / "f.zip", folder / "i.sqlite")["unit_m"], unit)

    def test_a_distance_that_matches_no_known_unit_is_refused(self):
        files = fx.feed_files()
        lines = files["shapes.txt"].splitlines()
        body = [",".join(r.split(",")[:4] + [str(float(r.split(",")[4]) * 0.3048 * 7)]) for r in lines[1:]]
        files["shapes.txt"] = chr(10).join([lines[0]] + body) + chr(10)
        folder = Path(tempfile.mkdtemp())
        fx.write_zip(folder / "f.zip", files)
        with self.assertRaisesRegex(FeedError, "Unrecognised"):
            build_database(folder / "f.zip", folder / "i.sqlite")

    def test_bad_feeds_are_refused_with_a_message(self):
        folder = Path(tempfile.mkdtemp())
        junk = folder / "junk.zip"
        junk.write_bytes(b"not a zip")
        with self.assertRaises(FeedError):
            build_database(junk, folder / "i.sqlite")
        with self.assertRaises(FeedError):
            build_database(folder / "missing.zip", folder / "i.sqlite")
        for name in ("stops.txt", "stop_times.txt", "calendar.txt"):
            with self.subTest(missing=name):
                fx.write_zip(folder / "m.zip", drop=(name,))
                with self.assertRaisesRegex(FeedError, name):
                    build_database(folder / "m.zip", folder / "i.sqlite")

    def test_a_huge_feed_is_refused(self):
        folder = Path(tempfile.mkdtemp())
        fx.write_zip(folder / "f.zip")
        with mock.patch.object(gtfs_store, "MAX_UNZIPPED_BYTES", 100):
            with self.assertRaisesRegex(FeedError, "200 MB"):
                build_database(folder / "f.zip", folder / "i.sqlite")

    def test_a_failed_build_keeps_the_old_index_and_leaves_no_leftovers(self):
        store, _, db_path = fx.build_fixture_store()
        before = db_path.read_bytes()
        bad = db_path.parent / "bad.zip"
        files = fx.feed_files()
        files["shapes.txt"] = "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"  # no shapes
        fx.write_zip(bad, files)
        with self.assertRaises(FeedError):
            build_database(bad, db_path)
        self.assertEqual(db_path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in db_path.parent.iterdir() if p.suffix == ".sqlite"), ["index.sqlite"])

    def test_route_colours_are_checked_before_they_reach_a_page(self):
        store, _, _ = fx.build_fixture_store()
        self.assertEqual(store.route("R3")["color"], "2b3a30")  # "bad color" replaced by the default
        self.assertEqual(store.route("R4")["color"], "2b3a30")  # empty replaced by the default
        self.assertEqual(store.route("R1")["color"], "ab6339")
        self.assertEqual(store.route("nope")["short_name"], "nope")

    def test_an_index_from_another_version_is_not_opened(self):
        _, _, db_path = fx.build_fixture_store()
        con = sqlite3.connect(db_path)
        con.execute("UPDATE feed SET value = '99' WHERE key = 'schema'")
        con.commit()
        con.close()
        with self.assertRaises(FeedError):
            GtfsStore(db_path)
        self.assertIsNone(gtfs_store.open_store(db_path))
        self.assertIsNone(gtfs_store.open_store(db_path.parent / "absent.sqlite"))


class TestServiceDays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def services(self, day):
        d = datetime.fromisoformat(day)
        return self.store.active_services(d.strftime("%Y%m%d"), d.weekday())

    def test_weekday_saturday_and_sunday_have_their_own_service(self):
        self.assertEqual(self.services(fx.WEDNESDAY), {"WK"})
        self.assertEqual(self.services(fx.SATURDAY), {"SA"})
        self.assertEqual(self.services(fx.SUNDAY), {"SU"})

    def test_a_date_exception_can_remove_one_service_and_add_another(self):
        self.assertEqual(self.services(fx.HOLIDAY_FRIDAY), {"SA"})  # a Friday running the Saturday schedule

    def test_a_date_with_no_service_and_dates_outside_the_feed(self):
        self.assertEqual(self.services("2025-12-31"), set())
        self.assertFalse(self.store.covers("20251231"))
        self.assertTrue(self.store.covers("20260101") and self.store.covers("20261231"))
        self.assertFalse(self.store.covers("20270101"))


class TestStopsAndTrips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def test_nearby_stops_are_sorted_by_distance_and_limited(self):
        near = self.store.stops_near(*fx.NEAR_A, 3000, 2)
        self.assertEqual([s["stop_id"] for s in near], ["A1", "B1"])
        self.assertLess(near[0]["straight_m"], near[1]["straight_m"])
        self.assertEqual(self.store.stops_near(*fx.NEAR_A, 20, 5), [])

    def test_a_stop_where_nobody_may_get_off_is_not_an_alighting_point(self):
        rows = self.store.departures(["A1"], ["B1"], ["WK"], 7 * 3600 + 600, limit=3)
        self.assertNotIn("nodrop", [r["trip_id"] for r in rows])
        self.assertEqual(rows[0]["trip_id"], "wk3")  # the regular 07:30

    def test_the_stop_must_come_before_the_other_on_the_same_trip(self):
        self.assertEqual(self.store.departures(["B1"], ["A1"], ["SA"], 0), [])  # Saturday has no trip towards A

    def test_empty_inputs_find_nothing(self):
        self.assertEqual(self.store.departures([], ["B1"], ["WK"], 0), [])
        self.assertEqual(self.store.departures(["A1"], ["B1"], [], 0), [])
        self.assertEqual(self.store.routes_connecting([], ["B1"]), [])

    def test_routes_connecting_lists_the_services_each_route_runs(self):
        found = {name: services for _, name, services in self.store.routes_connecting(["A1"], ["B1"])}
        self.assertEqual(found["65"], ["WK"])
        self.assertEqual(found["115"], ["SA", "SU"])
        self.assertEqual(self.store.routes_connecting(["A1"], ["E1"]), [])

    def test_the_line_between_two_stops_is_cut_from_the_shape(self):
        row = self.store.departures(["A1"], ["C1"], ["WK"], 6 * 3600, limit=1)[0]
        whole = self.store.shape_between(row["shape_id"], 0, row["alight_dist"])
        part = self.store.shape_between(row["shape_id"], row["board_dist"], row["alight_dist"] / 2)
        self.assertGreater(len(whole), len(part))
        self.assertGreaterEqual(len(part), 2)


class TestPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def find(self, day, hhmm, origin=START, dest=END):
        return find_bus(origin, dest, at(day, hhmm), store=self.store)

    def test_weekday_morning_gives_the_next_reachable_bus_with_both_walks(self):
        result = self.find(fx.WEDNESDAY, "07:00")
        self.assertEqual(result.status, "ok")
        bus = result.itinerary
        self.assertEqual((bus.route_name, bus.depart_time, bus.arrive_time), ("30", "07:30", "07:40"))  # not the no-drop 07:15
        self.assertEqual(bus.board.stop_id, "A1")
        self.assertEqual(bus.alight.stop_id, "B1")
        self.assertTrue(1.3 < bus.ride_km < 1.7)
        self.assertEqual(bus.total_min, bus.walk_to_min + bus.wait_min + bus.ride_min + bus.walk_from_min)
        self.assertEqual(bus.service_date, fx.WEDNESDAY)
        self.assertEqual(bus.next_departures, ("08:00", "08:30", "09:00"))
        self.assertEqual(bus.path[0], (fx.A[0], fx.A[1]))
        self.assertEqual(bus.path[-1], (fx.B[0], fx.B[1]))
        self.assertGreaterEqual(len(bus.path), 3)

    def test_a_bus_that_leaves_before_you_can_reach_the_stop_is_skipped(self):
        # 45 m is about a minute on foot; at 07:29:30 the 07:30 is out of reach, the 08:00 is next
        late = datetime.fromisoformat(f"{fx.WEDNESDAY}T07:29").replace(second=30)
        result = find_bus(START, END, late, store=self.store)
        self.assertEqual(result.itinerary.depart_time, "08:00")
        early = self.find(fx.WEDNESDAY, "07:27")
        self.assertEqual(early.itinerary.depart_time, "07:30")

    def test_leave_time_is_when_to_set_off_to_catch_it(self):
        bus = self.find(fx.WEDNESDAY, "07:00").itinerary
        self.assertTrue("07:00" <= bus.leave_time <= bus.depart_time)

    def test_weekend_uses_the_weekend_timetable_and_routes(self):
        sat = self.find(fx.SATURDAY, "09:30").itinerary
        self.assertEqual((sat.route_name, sat.depart_time, sat.arrive_time), ("115", "10:00", "10:05"))  # the weekend-only route is first
        names = {n for _, n, _ in self.store.routes_connecting(["A1"], ["B1"])}
        self.assertIn("65", names)  # exists, but only on weekdays
        sun = self.find(fx.SUNDAY, "10:30").itinerary
        self.assertEqual(sun.route_name, "30")
        self.assertNotEqual(sun.route_name, "65")

    def test_a_weekday_only_route_is_offered_on_weekdays_and_never_at_weekends(self):
        weekday = self.find(fx.WEDNESDAY, "09:15")
        self.assertEqual((weekday.itinerary.route_name, weekday.itinerary.arrive_time), ("65", "09:25"))  # the fast one
        for day in (fx.SATURDAY, fx.SUNDAY):
            routes = {self.find(day, f"{h:02d}:15").itinerary.route_name for h in range(8, 20)}
            self.assertNotIn("65", routes)

    def test_after_midnight_trips_belong_to_the_previous_service_day(self):
        # 00:10 on Thursday: the night trip left Wednesday 23:50 and calls at B1 at 24:05, i.e. 00:05
        late_evening = self.find(fx.WEDNESDAY, "23:45")
        self.assertEqual(late_evening.itinerary.route_name, "90")
        self.assertEqual(late_evening.itinerary.arrive_time, "00:05")  # shown as a clock time, past midnight
        after = self.find("2026-06-04", "00:00")  # Thursday just after midnight: nothing running yet
        self.assertIn(after.status, ("ok",))
        self.assertEqual(after.itinerary.route_name, "30")  # the first bus of Thursday, 06:00 ...
        self.assertEqual(after.itinerary.depart_time, "06:00")

    def test_a_trip_running_past_midnight_is_found_by_a_search_after_midnight(self):
        # Searching at 00:03 on Thursday must still see Wednesday's night trip if it has not yet reached the stop
        result = find_bus(place("far", (fx.B[0], fx.B[1] + 0.0)), place("c", (fx.C[0], fx.C[1])),
                          at("2026-06-04", "00:03"), store=self.store)
        # B1 was passed at 00:05 by the night trip (24:05): reachable only if the stop is at the start
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.itinerary.route_name, "90")

    def test_the_best_ride_is_the_one_that_arrives_first_not_the_one_that_leaves_first(self):
        result = self.find(fx.WEDNESDAY, "08:50")
        # the slow route 65 trip leaves first (08:55) but reaches B1 at 09:40; route 30 at 09:00 reaches it at 09:10
        self.assertEqual((result.itinerary.route_name, result.itinerary.depart_time, result.itinerary.arrive_time),
                         ("30", "09:00", "09:10"))

    def test_a_holiday_exception_changes_the_schedule(self):
        # Friday 2026-07-03 runs the Saturday timetable: first bus 08:00, hourly
        result = self.find(fx.HOLIDAY_FRIDAY, "06:00")
        self.assertEqual(result.itinerary.depart_time, "08:00")

    def test_no_more_buses_today_says_so_and_gives_the_next_day(self):
        result = self.find(fx.WEDNESDAY, "23:59")
        self.assertEqual(result.status, "no_more_that_day")
        self.assertIsNotNone(result.later)
        self.assertEqual(result.later.service_date, "2026-06-04")
        self.assertIn("after 23:59", result.note)
        self.assertIn("The next one is route 30", result.note)
        self.assertIsNone(result.itinerary)

    def test_no_service_at_all_that_day_says_so(self):
        store, _, _ = fx.build_fixture_store()
        with mock.patch.object(GtfsStore, "active_services", lambda self, day, wd: set() if day == "20260603" else {"WK"}):
            result = find_bus(START, END, at(fx.WEDNESDAY, "09:00"), store=store)
        self.assertEqual(result.status, "no_service_that_day")
        self.assertIn("no scheduled service", result.note)
        self.assertIsNotNone(result.later)

    def test_a_route_that_does_not_run_that_day_is_explained(self):
        # E1 is linked to C1 by a weekday-only route: on Saturday the link exists in the feed but does not run
        near_c, near_e = place("c", (fx.C[0] + 0.0004, fx.C[1])), place("e", fx.NEAR_E)
        result = self.find(fx.SATURDAY, "10:00", near_c, near_e)
        self.assertEqual(result.status, "no_service_that_day")
        self.assertIn("run on other days", result.note)
        self.assertIn("51", result.note)
        self.assertEqual(result.later.service_date, "2026-06-08")  # Monday

    def test_dates_outside_the_feed_are_reported_with_what_it_covers(self):
        result = self.find("2027-02-01", "09:00")
        self.assertEqual(result.status, "outside_feed")
        self.assertIn("covers", result.note)
        self.assertIn("update_transit", result.note)

    def test_no_stop_close_enough_is_reported_for_each_end(self):
        nowhere = place("lake", (42.60, -76.60))
        self.assertEqual(self.find(fx.WEDNESDAY, "09:00", nowhere, END).status, "no_stop_near_start")
        self.assertEqual(self.find(fx.WEDNESDAY, "09:00", START, nowhere).status, "no_stop_near_destination")

    def test_two_places_with_no_single_route_between_them_are_reported(self):
        result = self.find(fx.WEDNESDAY, "09:00", START, place("e", fx.NEAR_E))
        self.assertEqual(result.status, "no_direct_route")
        self.assertIn("transfers", result.note)

    def test_a_missing_index_says_how_to_build_it(self):
        with mock.patch.object(bus_planner, "open_store", return_value=None):
            result = find_bus(START, END, at(fx.WEDNESDAY, "09:00"))
        self.assertEqual(result.status, "not_installed")
        self.assertIn("python -m src.update_transit", result.note)

    def test_the_same_question_always_gets_the_same_answer(self):
        self.assertEqual(self.find(fx.WEDNESDAY, "10:10"), self.find(fx.WEDNESDAY, "10:10"))


class TestLocalTime(unittest.TestCase):
    def test_now_is_a_naive_local_datetime_to_the_minute(self):
        now = local_now()
        self.assertIsNone(now.tzinfo)
        self.assertEqual((now.second, now.microsecond), (0, 0))

    def test_the_fallback_follows_the_us_daylight_saving_rule(self):
        offset = bus_planner._us_eastern_offset_hours
        self.assertEqual(offset(datetime(2026, 1, 15, 12)), -5)
        self.assertEqual(offset(datetime(2026, 7, 15, 12)), -4)
        self.assertEqual(offset(datetime(2026, 3, 8, 6, 59)), -5)  # just before 02:00 EST on the second Sunday of March
        self.assertEqual(offset(datetime(2026, 3, 8, 7, 0)), -4)
        self.assertEqual(offset(datetime(2026, 11, 1, 5, 59)), -4)  # just before 02:00 EDT on the first Sunday of November
        self.assertEqual(offset(datetime(2026, 11, 1, 6, 0)), -5)

    def test_without_a_time_zone_database_it_still_works(self):
        with mock.patch("zoneinfo.ZoneInfo", side_effect=KeyError("America/New_York")):
            self.assertIsNone(local_now().tzinfo)


class TestBusInThePlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def setUp(self):
        patch = mock.patch.object(bus_planner, "open_store", return_value=self.store)
        patch.start()
        self.addCleanup(patch.stop)
        weather = mock.patch("src.c2_application_service.plan.current_weather", return_value=DRY)
        weather.start()
        self.addCleanup(weather.stop)
        # the plan geocodes text, so name the two test places through the sample list's own coordinates
        geo = mock.patch("src.c2_application_service.comparison.geocode",
                         side_effect=lambda text: {"start": START, "end": END}.get(text.strip().lower()))
        geo.start()
        self.addCleanup(geo.stop)
        routes = mock.patch("src.c2_application_service.comparison.get_route_options", side_effect=self._routes)
        routes.start()
        self.addCleanup(routes.stop)

    @staticmethod
    def _routes(origin, dest):
        from src.interfaces import RouteOption

        return (RouteOption("drive", 2.0, 5.0, "test"), RouteOption("walk", 1.6, 20.0, "test"),
                RouteOption("bike", 1.7, 7.0, "test"))

    def plan(self, when, **kw):
        return plan_commute("start", "end", when=when, **kw)

    def test_the_bus_is_one_more_compared_way_with_its_own_numbers(self):
        plan = self.plan(at(fx.WEDNESDAY, "07:00"))
        self.assertEqual([c.mode for c in plan.comparisons], ["drive", "walk", "bus"])
        bus = plan.comparisons[-1]
        drive = plan.comparisons[0]
        self.assertEqual(bus.distance_km, plan.bus.itinerary.ride_km)  # the ride along the route, not the drive distance
        self.assertEqual(bus.duration_min, plan.bus.itinerary.total_min)  # door to door, waits and walks included
        self.assertEqual(bus.co2e_g, round(plan.bus.itinerary.ride_km * 105))  # placeholder bus factor
        self.assertEqual(bus.difference_g, drive.co2e_g - bus.co2e_g)
        self.assertIn("test-1", bus.source)

    def test_no_bus_that_day_means_no_bus_row_and_a_reason(self):
        plan = self.plan(at(fx.WEDNESDAY, "23:59"))
        self.assertEqual([c.mode for c in plan.comparisons], ["drive", "walk"])
        self.assertEqual(plan.bus.status, "no_more_that_day")
        self.assertTrue(plan.bus.note)

    def test_the_bus_never_appears_when_the_data_is_not_installed(self):
        with mock.patch.object(bus_planner, "open_store", return_value=None):
            plan = self.plan(at(fx.WEDNESDAY, "07:00"))
        self.assertNotIn("bus", [c.mode for c in plan.comparisons])
        self.assertEqual(plan.bus.status, "not_installed")

    def test_rain_leaves_the_bus_as_the_greener_way_that_still_works(self):
        wet = WeatherForecast(precipitation_mm=2.0, forecast_timestamp="t", temperature_c=10.0, wind_kmh=5.0)
        with mock.patch("src.c2_application_service.plan.current_weather", return_value=wet):
            plan = self.plan(at(fx.WEDNESDAY, "07:00"))
        self.assertEqual(plan.recommendation.mode, "bus")
        self.assertIn("rain", dict(plan.recommendation.excluded)["walk"])

    def test_a_dry_day_still_prefers_walking_over_the_bus(self):
        self.assertEqual(self.plan(at(fx.WEDNESDAY, "07:00")).recommendation.mode, "walk")

    def test_the_bus_can_be_confirmed_like_any_other_way(self):
        from src.c2_application_service import confirm_trip
        from src.c3_data_adapter import reset_confirmed

        reset_confirmed()
        self.addCleanup(reset_confirmed)
        trip, _, errors = confirm_trip("start", "end", "bus", "2026-06-03", when=at(fx.WEDNESDAY, "07:00"))
        self.assertEqual(errors, [])
        self.assertEqual(trip.mode, "bus")
        _, _, errors = confirm_trip("start", "end", "bus", "2026-06-03", when=at(fx.WEDNESDAY, "23:59"))
        self.assertTrue(errors)  # no bus then, so it is not one of the compared options


class TestStartupLine(unittest.TestCase):
    def test_the_server_says_whether_the_schedule_was_found(self):
        try:
            from src.main_web import transit_status
        except ImportError:
            self.skipTest("Flask not installed")
        store, _, _ = fx.build_fixture_store()
        found = transit_status(store)
        self.assertIn("feed test-1", found)
        self.assertIn("20260101 to 20261231", found)
        with mock.patch("src.main_web.open_store", return_value=None):
            missing = transit_status()
        self.assertIn("not built", missing)
        self.assertIn("python -m src.update_transit", missing)


REAL_DB = Path(__file__).resolve().parent.parent / "data" / "tcat" / "tcat.sqlite"
ARTS_QUAD = Place("Arts Quad", -76.4835, 42.4491, "test")
COMMONS = Place("Ithaca Commons", -76.4968, 42.4396, "test")


@unittest.skipUnless(REAL_DB.exists(), "the real TCAT index is not built here (python -m src.update_transit)")
class TestRealFeed(unittest.TestCase):
    """Facts about the real 2026-09-22 TCAT feed. Skipped unless it has been downloaded and built."""

    @classmethod
    def setUpClass(cls):
        cls.store = GtfsStore(REAL_DB)
        cls.info = cls.store.feed_info()

    def test_the_feed_is_the_tcat_one_and_distances_are_feet(self):
        self.assertIn("Tompkins", self.info["agency"])
        self.assertAlmostEqual(float(self.info["distance_unit_m"]), 0.3048)

    def ride(self, day, hhmm):
        if not self.store.covers(day.replace("-", "")):
            self.skipTest("this date is outside the schedule that was downloaded")
        return find_bus(ARTS_QUAD, COMMONS, at(day, hhmm), store=self.store)

    def test_a_weekday_morning_has_a_direct_bus_with_a_believable_ride(self):
        bus = self.ride("2026-10-27", "08:00").itinerary
        self.assertIsNotNone(bus)
        self.assertTrue(1.5 < bus.ride_km < 8, bus.ride_km)  # a shape distance read as metres would be 3 times too big
        self.assertTrue(5 < bus.total_min < 60)
        self.assertLess(bus.board.lat, 42.5)

    def test_thanksgiving_has_no_service(self):
        if not self.store.covers("20261126"):
            self.skipTest("Thanksgiving is outside the schedule that was downloaded")
        self.assertEqual(self.ride("2026-11-26", "10:00").status, "no_service_that_day")

    def test_routes_that_do_not_run_at_weekends_are_never_offered_then(self):
        weekday_only = {"10", "36", "65", "81", "82"}  # no Saturday or Sunday service in this feed
        for day in ("2026-10-31", "2026-11-01"):
            result = self.ride(day, "09:00")
            if result.itinerary:
                self.assertNotIn(result.itinerary.route_name, weekday_only)


if __name__ == "__main__":
    unittest.main()
