"""Feasibility filter, recommendation and weather adapter checks. No network is used.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from unittest import mock

from src.c2_application_service import plan_commute, recommend_mode
from src.c3_data_adapter import weather_adapter
from src.interfaces import ModeComparison, Place, WeatherForecast


def row(mode, minutes, co2e_g, drive_g=1000):
    return ModeComparison(mode, 3.0, minutes, co2e_g, drive_g - co2e_g, "test")


# drive is fastest, bike is a little slower and clean, walk is slow and clean
ROWS = (row("drive", 8, 1000), row("walk", 30, 0), row("bike", 14, 0), row("bus", 18, 400))
DRY = WeatherForecast(precipitation_mm=0.0, forecast_timestamp="t", temperature_c=15.0, wind_kmh=10.0)


class TestRecommendation(unittest.TestCase):
    def test_walk_comes_before_bike_when_both_emit_the_same(self):
        rec = recommend_mode(ROWS, DRY)
        self.assertEqual(rec.mode, "walk")  # walk and bike both emit 0 g; walk is first in the priority

    def test_a_walk_over_the_time_limit_is_ruled_out_so_bike_is_next(self):
        rows = (row("drive", 8, 1000), row("walk", 40, 0), row("bike", 14, 0))
        rec = recommend_mode(rows, DRY)
        self.assertEqual(rec.mode, "bike")
        self.assertIn(("walk", "40 min is over the 30 min limit for walk"), rec.excluded)

    def test_bike_and_scooter_have_their_own_longer_time_limit(self):
        rows = (row("drive", 8, 1000), row("bike", 50, 0), row("scooter", 44, 20))
        rec = recommend_mode(rows, DRY)
        self.assertEqual(rec.mode, "scooter")
        self.assertIn("over the 45 min limit for bike", dict(rec.excluded)["bike"])

    def test_scooter_ranks_after_bike_and_before_bus(self):
        rows = (row("drive", 8, 1000), row("bus", 12, 400), row("scooter", 10, 20), row("bike", 10, 0))
        self.assertEqual(recommend_mode(rows, DRY).mode, "bike")
        self.assertEqual(recommend_mode(rows, DRY, not_feasible=("bike",)).mode, "scooter")
        self.assertEqual(recommend_mode(rows, DRY, not_feasible=("bike", "scooter")).mode, "bus")

    def test_rain_rules_out_walk_bike_and_scooter(self):
        wet = WeatherForecast(precipitation_mm=1.5, forecast_timestamp="t", temperature_c=10.0, wind_kmh=5.0)
        rows = ROWS + (row("scooter", 10, 20),)
        rec = recommend_mode(rows, wet)
        self.assertEqual(rec.mode, "bus")  # lowest emission among what rain leaves
        reasons = dict(rec.excluded)
        for mode in ("walk", "bike", "scooter"):
            self.assertIn("rain", reasons[mode])

    def test_freezing_and_strong_wind_rule_out_the_wheeled_ways_only(self):
        rows = ROWS + (row("scooter", 10, 20),)
        for weather, word in (
            (WeatherForecast(0.0, "t", temperature_c=-3.0, wind_kmh=5.0), "freezing"),
            (WeatherForecast(0.0, "t", temperature_c=10.0, wind_kmh=55.0), "wind"),
        ):
            with self.subTest(word=word):
                rec = recommend_mode(rows, weather)
                self.assertIn(word, dict(rec.excluded)["bike"])
                self.assertIn(word, dict(rec.excluded)["scooter"])
                self.assertNotIn("walk", dict(rec.excluded))

    def test_user_marked_mode_is_never_recommended(self):  # SRD 2.1.5
        rec = recommend_mode(ROWS, DRY, not_feasible=("walk",))
        self.assertEqual(rec.mode, "bike")
        self.assertEqual(dict(rec.excluded)["walk"], "you marked it not feasible")

    def test_nothing_eligible_falls_back_to_fastest_not_ruled_out_by_user(self):
        wet = WeatherForecast(precipitation_mm=5.0, forecast_timestamp="t")
        rows = (row("walk", 30, 0), row("bike", 14, 0))
        rec = recommend_mode(rows, wet, not_feasible=("bike",))
        self.assertEqual(rec.mode, "walk")
        self.assertIn("No option passed the weather and time checks", rec.reason)

    def test_when_only_driving_is_left_the_reason_says_it_is_the_fallback(self):
        wet = WeatherForecast(precipitation_mm=5.0, forecast_timestamp="t")
        rec = recommend_mode((row("drive", 8, 1000), row("walk", 12, 0)), wet)
        self.assertEqual(rec.mode, "drive")
        self.assertIn("driving is the fallback", rec.reason)
        self.assertIn("8 min", rec.reason)

    def test_every_mode_marked_not_feasible_gives_no_recommendation(self):
        rec = recommend_mode((row("walk", 30, 0), row("bike", 14, 0)), DRY, not_feasible=("walk", "bike"))
        self.assertEqual(rec.mode, "")

    def test_missing_weather_is_disclosed_and_rules_are_skipped(self):
        rec = recommend_mode(ROWS, None)
        self.assertIn("not available", rec.weather_note)
        self.assertEqual(rec.mode, "walk")

    def test_same_inputs_give_the_same_answer(self):
        self.assertEqual(recommend_mode(ROWS, DRY), recommend_mode(ROWS, DRY))

    def test_reason_restates_table_values(self):
        rec = recommend_mode(ROWS, DRY)
        self.assertIn("30 min", rec.reason)
        self.assertIn("1000 g less than driving", rec.reason)
        self.assertIn("22 min more than the fastest (drive)", rec.reason)


class TestPlan(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ)
        patch.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(patch.stop)
        weather = mock.patch("src.c2_application_service.plan.current_weather", return_value=DRY)
        weather.start()
        self.addCleanup(weather.stop)

    def modes(self, **kw):
        return [c.mode for c in plan_commute("Cornell Arts Quad", "Ithaca Commons", **kw).comparisons]

    def test_the_student_has_no_bike_or_scooter_unless_they_say_so(self):
        self.assertEqual(self.modes(), ["drive", "walk"])
        self.assertEqual(self.modes(have=("bike",)), ["drive", "walk", "bike"])
        self.assertEqual(self.modes(have=("scooter", "bike")), ["drive", "walk", "bike", "scooter"])

    def test_unknown_vehicles_are_ignored(self):
        self.assertEqual(self.modes(have=("rocket", "bus")), ["drive", "walk"])

    def test_the_scooter_takes_the_bike_route_and_speed(self):
        rows = {c.mode: c for c in plan_commute("Cornell Arts Quad", "Ithaca Commons", have=("bike", "scooter")).comparisons}
        self.assertEqual((rows["scooter"].distance_km, rows["scooter"].duration_min),
                         (rows["bike"].distance_km, rows["bike"].duration_min))
        self.assertIn("scooter is assumed to use the bike route", rows["scooter"].source)
        self.assertGreater(rows["scooter"].co2e_g, rows["bike"].co2e_g)  # placeholder factor above zero

    def test_the_bus_is_never_compared_yet(self):
        self.assertNotIn("bus", self.modes(have=("bike", "scooter")))

    def test_default_student_gets_walk_recommended_on_a_short_dry_trip(self):
        self.assertEqual(plan_commute("Cornell Arts Quad", "Ithaca Commons").recommendation.mode, "walk")

    def test_bad_places_give_errors_and_no_recommendation(self):
        plan = plan_commute("Cornell Arts Quad", "nowhere")
        self.assertEqual(plan.comparisons, ())
        self.assertIsNone(plan.recommendation)
        self.assertTrue(plan.errors)


class TestWeatherAdapter(unittest.TestCase):
    PLACE = Place("A", -76.48, 42.44, "test")

    def test_parses_current_block(self):
        reply = {"current": {"time": "2026-10-27T08:00", "temperature_2m": 11.7, "precipitation": 0.0, "wind_speed_10m": 8.9}}
        with mock.patch.object(weather_adapter, "_http_json", return_value=reply):
            weather = weather_adapter.current_weather(self.PLACE)
        self.assertEqual((weather.temperature_c, weather.precipitation_mm, weather.wind_kmh), (11.7, 0.0, 8.9))

    def test_failures_return_none(self):
        for effect in (OSError("down"),):
            with mock.patch.object(weather_adapter, "_http_json", side_effect=effect):
                self.assertIsNone(weather_adapter.current_weather(self.PLACE))
        with mock.patch.object(weather_adapter, "_http_json", return_value={"oops": 1}):
            self.assertIsNone(weather_adapter.current_weather(self.PLACE))


if __name__ == "__main__":
    unittest.main()
