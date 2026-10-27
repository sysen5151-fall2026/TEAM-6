"""Badge rules, campus tree goal, trip confirmation and the achievements pages. No network is used.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from datetime import date, timedelta
from unittest import mock

from src.c2_application_service import campus_goal, confirm_trip, evaluate_badges, load_demo_trips
from src.c2_application_service.achievements import CAMPUS_SEED, TREE_GOAL_G, counted_trips
from src.c3_data_adapter import confirmed_trips, reset_confirmed
from src.interfaces import ConfirmedTrip, WeatherForecast

try:
    from src.c1_web_front_end.web_app import create_app
except ImportError:
    create_app = None

DRY = WeatherForecast(precipitation_mm=0.0, forecast_timestamp="t", temperature_c=15.0, wind_kmh=5.0)


def trip(day, mode="bike", dest="Collegetown", km=3.0, diff=500.0, rec="", origin="Home"):
    return ConfirmedTrip(day, mode, origin, dest, km, 0.0, diff, rec)


def badge(trips, badge_id):
    return next(b for b in evaluate_badges(trips) if b.id == badge_id)


class TestBadgeRules(unittest.TestCase):
    def test_no_trips_earns_nothing(self):
        self.assertFalse(any(b.earned for b in evaluate_badges([])))

    def test_first_step_needs_a_low_carbon_trip_not_a_drive(self):
        self.assertFalse(badge([trip("2026-10-05", mode="drive", diff=0)], "first_step").earned)
        self.assertTrue(badge([trip("2026-10-05", mode="walk")], "first_step").earned)

    def test_green_starter_boundary(self):
        self.assertFalse(badge([trip("2026-10-05", diff=999)], "green_starter").earned)
        self.assertTrue(badge([trip("2026-10-05", diff=1000)], "green_starter").earned)

    def test_five_day_flow_needs_four_different_days_in_one_week(self):
        week = ["2026-10-05", "2026-10-06", "2026-10-07"]  # Mon-Wed
        self.assertEqual(badge([trip(d, dest=f"P{d}") for d in week], "five_day_flow").progress, 3)
        self.assertTrue(badge([trip(d, dest=f"P{d}") for d in week + ["2026-10-08"]], "five_day_flow").earned)
        split = [trip("2026-10-09"), trip("2026-10-12"), trip("2026-10-13"), trip("2026-10-14")]  # Fri + next week
        self.assertFalse(badge(split, "five_day_flow").earned)

    def test_campus_explorer_counts_distinct_places(self):
        same = [trip(f"2026-10-0{i}", dest="Collegetown") for i in (5, 6, 7, 8, 9)]
        self.assertEqual(badge(same, "campus_explorer").progress, 1)
        five = [trip(f"2026-10-0{i}", dest=f"Place {i}") for i in (5, 6, 7, 8, 9)]
        self.assertTrue(badge(five, "campus_explorer").earned)

    def test_plan_keeper_counts_trips_matching_the_recommendation(self):
        kept = [trip(f"2026-10-{d:02d}", rec="bike", dest=f"P{d}") for d in (5, 6, 7, 8)]
        self.assertFalse(badge(kept, "plan_keeper").earned)
        self.assertTrue(badge(kept + [trip("2026-10-09", rec="bike", dest="P9")], "plan_keeper").earned)
        self.assertEqual(badge([trip("2026-10-05", rec="walk")], "plan_keeper").progress, 0)

    def test_car_free_week_is_spoiled_by_a_drive_and_needs_three_trips(self):
        free = [trip("2026-10-05", dest="A"), trip("2026-10-06", dest="B"), trip("2026-10-07", dest="C")]
        self.assertTrue(badge(free, "car_free_week").earned)
        self.assertFalse(badge(free + [trip("2026-10-08", mode="drive", diff=0)], "car_free_week").earned)
        self.assertFalse(badge(free[:2], "car_free_week").earned)

    def test_consistency_needs_consecutive_weeks(self):
        weekly = [trip(d, dest=d) for d in ("2026-10-05", "2026-10-12", "2026-10-19")]
        self.assertEqual(badge(weekly, "consistency_champion").progress, 3)
        self.assertTrue(badge(weekly + [trip("2026-10-26", dest="x")], "consistency_champion").earned)
        gap = [trip(d, dest=d) for d in ("2026-10-05", "2026-10-12", "2026-10-26", "2026-11-02")]
        self.assertEqual(badge(gap, "consistency_champion").progress, 2)

    def test_same_trips_always_give_the_same_badges(self):
        trips = [trip("2026-10-05"), trip("2026-10-06", dest="B")]
        self.assertEqual(evaluate_badges(trips), evaluate_badges(trips))


class TestAntiGaming(unittest.TestCase):
    def test_only_two_trips_per_day_count(self):
        many = [trip("2026-10-05", dest=f"P{i}") for i in range(6)]
        self.assertEqual(len(counted_trips(many)), 2)
        self.assertEqual(badge(many, "green_starter").progress, 1000)

    def test_repeated_trip_counts_once(self):
        self.assertEqual(len(counted_trips([trip("2026-10-05"), trip("2026-10-05")])), 1)

    def test_distance_over_the_cap_counts_as_the_cap(self):
        far = trip("2026-10-05", km=500.0, diff=100_000.0)  # would be 100 kg uncapped
        self.assertEqual(badge([far], "green_starter").progress, 1000)  # capped to 10 kg, then min(target)
        self.assertEqual(campus_goal([far]).total_g, round(CAMPUS_SEED["difference_g"] + 10_000))


class TestCampusGoal(unittest.TestCase):
    def test_no_trips_is_the_sample_seed_only(self):
        goal = campus_goal([])
        self.assertEqual(goal.total_g, CAMPUS_SEED["difference_g"])
        self.assertEqual(goal.trees_reached, 0)
        self.assertEqual(goal.students, CAMPUS_SEED["students"])
        self.assertIn("sample data", goal.sample_note)

    def test_tree_is_reached_at_the_goal_and_progress_restarts(self):
        need = TREE_GOAL_G - CAMPUS_SEED["difference_g"]
        below = campus_goal([trip("2026-10-05", diff=need - 1)])
        at = campus_goal([trip("2026-10-05", diff=need)])
        self.assertEqual((below.trees_reached, at.trees_reached), (0, 1))
        self.assertEqual(at.into_next_g, 0)
        self.assertEqual(at.students, CAMPUS_SEED["students"] + 1)

    def test_tree_planter_needs_a_tree_and_your_own_counted_trip(self):
        need = TREE_GOAL_G - CAMPUS_SEED["difference_g"]
        self.assertFalse(badge([], "tree_planter").earned)
        self.assertFalse(badge([trip("2026-10-05", diff=need - 1)], "tree_planter").earned)
        self.assertTrue(badge([trip("2026-10-05", diff=need)], "tree_planter").earned)


@unittest.skipIf(create_app is None, "Flask not installed")
class TestConfirmAndPages(unittest.TestCase):
    def setUp(self):
        reset_confirmed()
        self.addCleanup(reset_confirmed)
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(env.stop)
        weather = mock.patch("src.c2_application_service.plan.current_weather", return_value=DRY)
        weather.start()
        self.addCleanup(weather.stop)
        self.client = create_app().test_client()
        self.today = date.today().isoformat()
        self.form = {"origin": "Cornell Arts Quad", "destination": "Ithaca Commons", "mode": "bike", "date": self.today}

    def test_confirm_recomputes_numbers_and_earns_first_step(self):
        trip_, new, errors = confirm_trip("Cornell Arts Quad", "Ithaca Commons", "bike", self.today)
        self.assertEqual(errors, [])
        self.assertEqual(new, ("First Step",))
        self.assertGreater(trip_.difference_g, 0)
        self.assertEqual(trip_.recommended_mode, "bike")
        self.assertEqual(len(confirmed_trips()), 1)

    def test_duplicate_future_and_bad_inputs_are_refused(self):
        confirm_trip("Cornell Arts Quad", "Ithaca Commons", "bike", self.today)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cases = (
            ("Cornell Arts Quad", "Ithaca Commons", "bike", self.today),  # duplicate
            ("Cornell Arts Quad", "Ithaca Commons", "bike", tomorrow),  # not yet happened
            ("Cornell Arts Quad", "Ithaca Commons", "bike", "yesterday"),
            ("Cornell Arts Quad", "Ithaca Commons", "rocket", self.today),
            ("Cornell Arts Quad", "Ithaca Commons", "bus", self.today),  # no bus time was entered
            ("Cornell Arts Quad", "nowhere", "bike", self.today),
        )
        for case in cases:
            with self.subTest(case=case):
                trip_, new, errors = confirm_trip(*case)
                self.assertIsNone(trip_)
                self.assertTrue(errors)
        self.assertEqual(len(confirmed_trips()), 1)

    def test_pages_load_and_confirm_goes_to_the_done_page_with_the_new_badge(self):
        for path in ("/achievements", "/garden"):
            self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.post("/confirm", data=self.form)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/done/0"))  # not the achievements page
        page = self.client.get(response.headers["Location"]).data
        self.assertIn(b"Congratulations", page)
        self.assertIn(b"New badge", page)
        self.assertIn(b"First Step", page)

    def test_done_page_has_no_popup_without_a_new_badge_and_ignores_made_up_names(self):
        self.client.post("/confirm", data=self.form)
        plain = self.client.get("/done/0").data
        self.assertNotIn(b"<dialog", plain)
        faked = self.client.get("/done/0?new=Consistency+Champion").data  # not earned: must not appear
        self.assertNotIn(b"<dialog", faked)

    def test_choosing_to_drive_logs_the_trip_without_congratulating(self):
        response = self.client.post("/confirm", data={**self.form, "mode": "drive"})
        page = self.client.get(response.headers["Location"]).data
        self.assertIn(b"Trip logged", page)
        self.assertNotIn(b"Congratulations", page)

    def test_done_page_with_an_unknown_index_goes_back_to_planning(self):
        self.assertEqual(self.client.get("/done/99").status_code, 302)

    def test_achievements_page_reviews_trips_and_lists_badges_still_to_go(self):
        self.client.post("/confirm", data=self.form)
        page = self.client.get("/achievements").data
        self.assertIn(b"Cornell Arts Quad", page)  # the trip history
        self.assertIn(b"Still to go", page)
        self.assertIn(b"Earned", page)
        self.assertNotIn(b"Trip confirmed", page)  # no confirmation banner here any more

    def test_garden_draws_one_tree_per_reached_goal_and_a_growing_sapling(self):
        empty = self.client.get("/garden").data
        self.assertEqual(empty.count(b'class="tree"'), 0)
        self.assertEqual(empty.count(b'class="sapling"'), 1)
        load_demo_trips()
        confirm_trip("Cornell Arts Quad", "Ithaca Commons", "bike", self.today)  # reaches the first tree
        grown = self.client.get("/garden").data
        self.assertEqual(grown.count(b'class="tree"'), 1)
        self.assertIn(b"1 tree planted", grown)

    def test_confirm_errors_show_on_the_page_without_crashing(self):
        for data in ({}, {**self.form, "mode": "rocket"}, {**self.form, "transit_minutes": "abc", "mode": "bus"}):
            with self.subTest(data=data):
                response = self.client.post("/confirm", data=data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'role="alert"', response.data)

    def test_demo_data_then_reset(self):
        self.client.post("/demo")
        self.assertEqual(len(confirmed_trips()), load_demo_trips() + 12)  # second load adds nothing
        page = self.client.get("/achievements").data
        self.assertIn(b"Earned", page)
        self.assertIn(b"sample data", self.client.get("/garden").data)  # the campus share is disclosed as sample data
        self.client.post("/reset")
        self.assertEqual(confirmed_trips(), ())

    def test_demo_stops_just_short_of_a_tree_and_one_trip_reaches_it(self):
        load_demo_trips()
        self.assertEqual(campus_goal(confirmed_trips()).trees_reached, 0)
        _, new, errors = confirm_trip("Cornell Arts Quad", "Ithaca Commons", "bike", self.today)
        self.assertEqual(errors, [])
        self.assertIn("Tree Planter", new)
        self.assertEqual(campus_goal(confirmed_trips()).trees_reached, 1)

    def test_plan_page_offers_a_choose_button(self):
        data = {"origin": "Cornell Arts Quad", "destination": "Ithaca Commons"}
        self.assertIn(b"Choose this way", self.client.post("/", data=data).data)


if __name__ == "__main__":
    unittest.main()
