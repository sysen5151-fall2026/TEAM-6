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
    def test_dry_day_prefers_lowest_emission_within_the_time_limit(self):
        rec = recommend_mode(ROWS, DRY)
        self.assertEqual(rec.mode, "bike")  # walk is 22 min over the fastest, past the 10 min limit
        self.assertIn(("walk", "22 min more than the fastest, over your 10 min limit"), rec.excluded)

    def test_rain_rules_out_walk_and_bike(self):
        wet = WeatherForecast(precipitation_mm=1.5, forecast_timestamp="t", temperature_c=10.0, wind_kmh=5.0)
        rec = recommend_mode(ROWS, wet)
        self.assertEqual(rec.mode, "bus")  # lowest emission among what rain leaves
        reasons = dict(rec.excluded)
        self.assertIn("rain", reasons["walk"])
        self.assertIn("rain", reasons["bike"])

    def test_freezing_and_strong_wind_rule_out_bike_only(self):
        for weather, word in (
            (WeatherForecast(0.0, "t", temperature_c=-3.0, wind_kmh=5.0), "freezing"),
            (WeatherForecast(0.0, "t", temperature_c=10.0, wind_kmh=55.0), "wind"),
        ):
            with self.subTest(word=word):
                rec = recommend_mode(ROWS, weather, max_extra_min=60)
                self.assertIn(word, dict(rec.excluded)["bike"])
                self.assertNotIn("walk", dict(rec.excluded))

    def test_user_marked_mode_is_never_recommended(self):  # SRD 2.1.5
        rec = recommend_mode(ROWS, DRY, not_feasible=("bike",), max_extra_min=60)
        self.assertEqual(rec.mode, "walk")
        self.assertEqual(dict(rec.excluded)["bike"], "you marked it not feasible")

    def test_nothing_eligible_falls_back_to_fastest_not_ruled_out_by_user(self):
        wet = WeatherForecast(precipitation_mm=5.0, forecast_timestamp="t")
        rows = (row("walk", 30, 0), row("bike", 14, 0))
        rec = recommend_mode(rows, wet, not_feasible=("bike",))
        self.assertEqual(rec.mode, "walk")
        self.assertIn("No option met all of your limits", rec.reason)

    def test_every_mode_marked_not_feasible_gives_no_recommendation(self):
        rec = recommend_mode((row("walk", 30, 0), row("bike", 14, 0)), DRY, not_feasible=("walk", "bike"))
        self.assertEqual(rec.mode, "")

    def test_missing_weather_is_disclosed_and_rules_are_skipped(self):
        rec = recommend_mode(ROWS, None)
        self.assertIn("not available", rec.weather_note)
        self.assertEqual(rec.mode, "bike")

    def test_same_inputs_give_the_same_answer(self):
        self.assertEqual(recommend_mode(ROWS, DRY), recommend_mode(ROWS, DRY))

    def test_reason_restates_table_values(self):
        rec = recommend_mode(ROWS, DRY)
        self.assertIn("14 min", rec.reason)
        self.assertIn("1000 g less than driving", rec.reason)
        self.assertIn("6 min more than the fastest (drive)", rec.reason)


class TestPlanWithBus(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ)
        patch.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(patch.stop)
        weather = mock.patch("src.c2_application_service.plan.current_weather", return_value=DRY)
        weather.start()
        self.addCleanup(weather.stop)

    def test_bus_only_appears_when_the_commuter_enters_a_time(self):
        without = plan_commute("Cornell Arts Quad", "Ithaca Commons")
        with_bus = plan_commute("Cornell Arts Quad", "Ithaca Commons", transit_minutes=25)
        self.assertEqual({c.mode for c in without.comparisons}, {"drive", "walk", "bike"})
        bus = next(c for c in with_bus.comparisons if c.mode == "bus")
        self.assertEqual(bus.duration_min, 25)
        self.assertIn("entered by you", bus.source)

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
