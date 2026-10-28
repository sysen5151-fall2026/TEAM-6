"""Several bus routes between the same two places: the planner offers each, the Commuter picks one.

Uses the invented feed in tests/gtfs_fixture.py. At 09:15 on a weekday from stop A1 to stop B1:
route 65 (the fast weekday-only one) leaves 09:20 and arrives 09:25; route 30 leaves 09:30 and
arrives 09:40. On Saturday route 115 (weekend only) beats route 30.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

try:
    from src.c1_web_front_end.web_app import create_app
    from tests.webhelper import make_client, store_of
except ImportError:  # Flask is the only non-standard dependency
    create_app = make_client = store_of = None

from src.c2_application_service import bus_planner, confirm_trip, plan_commute
from src.c2_application_service.bus_planner import find_bus
from src.c3_data_adapter import confirmed_trips, reset_confirmed
from src.c3_data_adapter.gtfs_store import GtfsStore
from src.interfaces import Place, RouteOption, WeatherForecast

from tests import gtfs_fixture as fx

DRY = WeatherForecast(precipitation_mm=0.0, forecast_timestamp="t", temperature_c=15.0, wind_kmh=5.0)
START, END = Place("Start", fx.NEAR_A[1], fx.NEAR_A[0], "test"), Place("End", fx.NEAR_B[1], fx.NEAR_B[0], "test")


def at(day, hhmm):
    return datetime.fromisoformat(f"{day}T{hhmm}")


class TestPlannerOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def find(self, day, hhmm):
        return find_bus(START, END, at(day, hhmm), store=self.store)

    def test_each_route_that_links_the_places_gets_its_best_ride(self):
        result = self.find(fx.WEDNESDAY, "09:15")
        self.assertEqual([o.route_name for o in result.options], ["65", "30"])
        self.assertEqual([o.arrive_time for o in result.options], ["09:25", "09:40"])  # earliest arrival first
        self.assertEqual(result.itinerary, result.options[0])  # the best one is also the default
        self.assertEqual(len({o.route_id for o in result.options}), 2)  # one ride per route

    def test_a_route_is_shown_once_with_its_earliest_arrival(self):
        route30 = self.find(fx.WEDNESDAY, "09:15").options[1]
        self.assertEqual((route30.depart_time, route30.arrive_time), ("09:30", "09:40"))  # not the later 10:00
        self.assertEqual(route30.next_departures[:2], ("10:00", "10:30"))  # the later ones are its "next" list

    def test_each_option_has_its_own_line_stops_and_times(self):
        fast, slow = self.find(fx.WEDNESDAY, "09:15").options
        self.assertEqual(fast.next_departures, ())  # route 65 has no later trip that morning
        for option in (fast, slow):
            self.assertEqual(option.board.stop_id, "A1")
            self.assertEqual(option.alight.stop_id, "B1")
            self.assertGreaterEqual(len(option.path), 3)
        self.assertGreater(slow.total_min, fast.total_min)

    def test_only_one_option_when_only_one_route_runs(self):
        result = self.find(fx.WEDNESDAY, "07:00")
        self.assertEqual([o.route_name for o in result.options], ["30"])

    def test_the_weekend_offers_the_weekend_routes_only(self):
        self.assertEqual([o.route_name for o in self.find(fx.SATURDAY, "09:30").options], ["115", "30"])
        weekday_only = {"65"}
        for day in (fx.SATURDAY, fx.SUNDAY):
            names = {o.route_name for h in range(8, 20) for o in self.find(day, f"{h:02d}:15").options}
            self.assertFalse(names & weekday_only)

    def test_a_route_that_only_runs_much_later_is_not_offered_as_an_alternative(self):
        # the night route 90 leaves at 23:50: a real route, but not a choice for someone leaving at 09:15
        routes = {o.route_name for o in self.find(fx.WEDNESDAY, "09:15").options}
        self.assertNotIn("90", routes)
        late_evening = {o.route_name for o in self.find(fx.WEDNESDAY, "23:45").options}
        self.assertEqual(late_evening, {"90"})  # at night it is the only one, so it is offered
        with mock.patch.object(bus_planner, "OPTION_WINDOW_S", 24 * 3600):
            self.assertIn("90", {o.route_name for o in self.find(fx.WEDNESDAY, "09:15").options})

    def test_the_number_of_options_is_capped(self):
        with mock.patch.object(bus_planner, "MAX_OPTIONS", 1):
            self.assertEqual([o.route_name for o in self.find(fx.WEDNESDAY, "09:15").options], ["65"])

    def test_no_bus_means_no_options(self):
        result = self.find(fx.WEDNESDAY, "23:59")
        self.assertEqual((result.options, result.itinerary), ((), None))
        self.assertIsNotNone(result.later)

    def test_busy_routes_do_not_crowd_out_a_route_with_few_trips(self):
        seen = {}
        real = GtfsStore.departures

        def spy(self_, *args, **kwargs):
            seen["limit"] = kwargs.get("limit")
            return real(self_, *args, **kwargs)

        with mock.patch.object(GtfsStore, "departures", spy):
            self.find(fx.WEDNESDAY, "09:15")
        self.assertEqual(seen["limit"], bus_planner.DEPARTURES_LOOKED_AT)
        self.assertGreater(bus_planner.DEPARTURES_LOOKED_AT, 80)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, _, _ = fx.build_fixture_store()

    def setUp(self):
        reset_confirmed()
        self.addCleanup(reset_confirmed)
        for target, kwargs in (
            ("src.c2_application_service.bus_planner.open_store", {"return_value": self.store}),
            ("src.c2_application_service.plan.current_weather", {"return_value": DRY}),
            ("src.c2_application_service.comparison.geocode",
             {"side_effect": lambda text: {"start": START, "end": END}.get(text.strip().lower())}),
            ("src.c2_application_service.comparison.get_route_options", {"side_effect": self._routes}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def _routes(origin, dest):
        return (RouteOption("drive", 2.0, 5.0, "test"), RouteOption("walk", 1.6, 20.0, "test"),
                RouteOption("bike", 1.7, 7.0, "test"))


class TestPlanChoice(Base):
    WHEN = at(fx.WEDNESDAY, "09:15")

    def plan(self, **kw):
        return plan_commute("start", "end", when=self.WHEN, **kw)

    def bus_row(self, plan):
        return next(c for c in plan.comparisons if c.mode == "bus")

    def test_by_default_the_bus_row_is_the_ride_that_arrives_first(self):
        plan = self.plan()
        self.assertEqual(plan.bus_choice, "R3")
        self.assertEqual(len(plan.bus_rows), 2)
        self.assertEqual(self.bus_row(plan), plan.bus_rows[0])

    def test_picking_a_route_builds_the_bus_row_from_it(self):
        plan = self.plan(bus_route="R1")
        self.assertEqual(plan.bus_choice, "R1")
        self.assertEqual(self.bus_row(plan), plan.bus_rows[1])
        self.assertGreater(self.bus_row(plan).duration_min, self.plan().bus_rows[0].duration_min)
        self.assertEqual([c.mode for c in plan.comparisons].count("bus"), 1)  # one bus row, not one per route

    def test_an_unknown_route_falls_back_to_the_best(self):
        for junk in ("nope", "", "R9", "R1; drop table"):
            with self.subTest(route=junk):
                self.assertEqual(self.plan(bus_route=junk).bus_choice, "R3")

    def test_each_option_has_its_own_numbers(self):
        rows = self.plan().bus_rows
        self.assertEqual([r.mode for r in rows], ["bus", "bus"])
        for option, row in zip(self.plan().bus.options, rows):
            self.assertEqual(row.distance_km, option.ride_km)
            self.assertEqual(row.duration_min, option.total_min)
            self.assertEqual(row.co2e_g, round(option.ride_km * 105))

    def test_the_recommendation_uses_the_picked_route(self):
        wet = WeatherForecast(precipitation_mm=2.0, forecast_timestamp="t", temperature_c=10.0, wind_kmh=5.0)
        with mock.patch("src.c2_application_service.plan.current_weather", return_value=wet):
            default = self.plan()
            picked = self.plan(bus_route="R1")
        self.assertEqual(default.recommendation.mode, "bus")
        self.assertIn(f"{default.bus_rows[0].duration_min:g} min", default.recommendation.reason)
        self.assertIn(f"{picked.bus_rows[1].duration_min:g} min", picked.recommendation.reason)

    def test_with_no_bus_there_is_nothing_to_choose(self):
        plan = plan_commute("start", "end", when=at(fx.WEDNESDAY, "23:59"), bus_route="R1")
        self.assertEqual((plan.bus_rows, plan.bus_choice), ((), ""))


class TestConfirmChoice(Base):
    WHEN = at(fx.WEDNESDAY, "09:15")
    DAY = fx.WEDNESDAY

    def confirm(self, route="", mode="bus"):
        return confirm_trip("start", "end", mode, self.DAY, when=self.WHEN, bus_route=route)

    def test_the_trip_records_the_route_that_was_picked_and_its_numbers(self):
        trip, _, errors = self.confirm("R1")
        self.assertEqual(errors, [])
        self.assertEqual(trip.route, "30")
        row = plan_commute("start", "end", when=self.WHEN, bus_route="R1").bus_rows[1]
        self.assertEqual((trip.distance_km, trip.co2e_g), (row.distance_km, row.co2e_g))

    def test_without_a_pick_it_is_the_ride_that_arrives_first(self):
        trip, _, _ = self.confirm()
        self.assertEqual(trip.route, "65")

    def test_a_second_bus_of_the_same_trip_and_day_is_refused_whatever_the_route(self):
        self.confirm("R3")
        trip, _, errors = self.confirm("R1")
        self.assertIsNone(trip)
        self.assertIn("already confirmed", errors[0])
        self.assertEqual(len(confirmed_trips()), 1)

    def test_other_ways_have_no_route(self):
        trip, _, _ = confirm_trip("start", "end", "walk", self.DAY, when=self.WHEN, bus_route="R1")
        self.assertEqual(trip.route, "")


@unittest.skipIf(create_app is None, "Flask not installed")
class TestPageChoice(Base):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(env.stop)
        self.client = make_client()
        self.trips = store_of(self.client, self)
        self.form = {"origin": "Cornell Arts Quad", "destination": "Ithaca Commons"}
        # the page geocodes the sample places, whose coordinates are the fixture's stops
        for target in ("src.c2_application_service.comparison.geocode",):
            mock.patch.stopall()
        self.setUp_patches()

    def setUp_patches(self):
        for target, kwargs in (
            ("src.c2_application_service.bus_planner.open_store", {"return_value": self.store}),
            ("src.c2_application_service.plan.current_weather", {"return_value": DRY}),
            ("src.c2_application_service.comparison.get_route_options", {"side_effect": self._routes}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def page(self, when="2026-06-03T09:15", **extra):
        return self.client.post("/", data={**self.form, "when": when, **extra}).get_data(as_text=True)

    def test_several_routes_are_offered_as_a_pick_with_the_best_ticked(self):
        page = self.page()
        self.assertIn("2 routes go there: pick one", page)
        self.assertIn('name="bus_route" value="R3" checked', page)
        self.assertIn('name="bus_route" value="R1"', page)
        self.assertNotIn('name="bus_route" value="R1" checked', page)
        self.assertIn("09:20 → 09:25", page)
        self.assertIn("09:30 → 09:40", page)

    def test_the_card_shows_the_ticked_route_in_full(self):
        best = self.page()
        self.assertIn("Bus 09:20 → 09:25", best)
        self.assertIn(">65</span> to Downtown", best)
        picked = self.page(bus_route="R1")
        self.assertIn('name="bus_route" value="R1" checked', picked)
        self.assertIn("Bus 09:30 → 09:40", picked)
        self.assertIn(">30</span> to Downtown", picked)

    def test_one_route_means_no_pick(self):
        page = self.page(when="2026-06-03T07:00")
        self.assertNotIn('<input type="radio" name="bus_route"', page)  # nothing to pick between
        self.assertNotIn("routes go there: pick one", page)
        self.assertIn('name="mode" value="bus"', page)

    def test_the_card_has_the_pieces_the_script_switches_and_the_data_for_every_route(self):
        page = self.page()
        for needle in ('id="bus-time"', 'id="bus-km"', 'id="bus-co2"', 'id="bus-save"', 'id="bus-line"', 'id="bus-steps"',
                       '"route_id": "R3"', '"route_id": "R1"', "function showBus", "function selectedBus"):
            self.assertIn(needle, page)

    def test_the_picked_route_is_recorded(self):
        response = self.client.post("/confirm", data={**self.form, "mode": "bus", "date": "2026-06-03",
                                                      "when": "2026-06-03T09:15", "bus_route": "R1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.trips.all()[0].route, "30")
        self.assertIn("bus 30", self.client.get("/achievements").get_data(as_text=True))

    def test_a_made_up_route_in_the_form_does_nothing_harmful(self):
        response = self.client.post("/confirm", data={**self.form, "mode": "bus", "date": "2026-06-03",
                                                      "when": "2026-06-03T09:15", "bus_route": "<script>"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.trips.all()[0].route, "65")  # fell back to the best

    def test_the_map_endpoint_lists_every_option_with_its_line(self):
        reply = self.client.get("/route-lines?olat=42.4491&olon=-76.4835&dlat=42.4396&dlon=-76.4968&when=2026-06-03T09:15")
        bus = reply.get_json()["bus"]
        self.assertEqual([o["route"] for o in bus["options"]], ["65", "30"])
        for option in bus["options"]:
            self.assertGreaterEqual(len(option["path"]), 3)
            self.assertEqual((option["board"]["name"], option["alight"]["name"]), ("Stop A1", "Stop B1"))
        self.assertEqual((bus["route"], bus["arrive"]), ("65", "09:25"))  # the best, as before

    def test_the_map_script_draws_every_route_and_thickens_the_picked_one(self):
        page = self.page()
        for needle in ("routes go there", "opacity: 0.45", "pickedBus"):
            self.assertIn(needle, page)


REAL_DB = Path(__file__).resolve().parent.parent / "data" / "tcat" / "tcat.sqlite"


@unittest.skipUnless(REAL_DB.exists(), "the real TCAT index is not built here (python -m src.update_transit)")
class TestRealFeedOptions(unittest.TestCase):
    def test_a_busy_pair_of_places_has_several_routes_each_once(self):
        store = GtfsStore(REAL_DB)
        if not store.covers("20261027"):
            self.skipTest("this date is outside the schedule that was downloaded")
        goldwin = Place("Goldwin", -76.4835, 42.4491, "t")
        commons = Place("Commons", -76.4968, 42.4396, "t")
        result = find_bus(goldwin, commons, datetime(2026, 10, 27, 10, 0), store=store)
        self.assertGreaterEqual(len(result.options), 2)
        self.assertLessEqual(len(result.options), bus_planner.MAX_OPTIONS)
        ids = [o.route_id for o in result.options]
        self.assertEqual(len(ids), len(set(ids)))
        arrivals = [(o.arrive_destination, o.depart_time) for o in result.options]
        self.assertEqual(result.itinerary, result.options[0])
        self.assertEqual(len(arrivals), len(result.options))


if __name__ == "__main__":
    unittest.main()
