"""UC.1 walking-skeleton checks. Each test names the SRD requirement it exercises.

Run:  python -m unittest discover -s tests -t .
"""

import unittest
from unittest import mock

from src.c3_data_adapter.data_adapter import reset_store
from src.interfaces import WeatherForecast
from src.x1_commuter_sim import run_uc1


class TestUC1EndToEnd(unittest.TestCase):
    def setUp(self):
        reset_store()

    def test_primary_path_runs_and_returns_result(self):
        out = run_uc1()  # drive 2.5 km, dry day
        self.assertIn("Estimated CO2e for this trip: 480 g", out)  # 2.5 km x 192 (placeholder)
        self.assertIn("Always-drive baseline: 480 g", out)

    def test_short_dry_trip_gets_walk_alternative(self):  # SRD 2.1.4
        self.assertIn("Suggested alternative: walk", run_uc1())

    def test_infeasible_mode_is_never_recommended(self):  # SRD 2.1.5
        out = run_uc1(not_feasible_modes=("walk",))
        self.assertIn("Suggested alternative: bike", out)
        self.assertNotIn("Suggested alternative: walk", out)

    def test_long_trip_gets_no_alternative(self):  # SRD 2.1.4 rule
        self.assertIn("No alternative suggested", run_uc1(distance_km=8))

    def test_rain_blocks_walk_bike(self):  # SRD 2.1.4 uses forecast weather
        wet = WeatherForecast(precipitation_mm=2.0, forecast_timestamp="t")
        with mock.patch("src.c3_data_adapter.data_adapter.return_weather_forecast", return_value=wet):
            self.assertIn("No alternative suggested", run_uc1())

    def test_result_discloses_method_and_labels_estimate(self):  # SRD 2.1.3, 2.4.4
        out = run_uc1()
        self.assertIn("version stub-0", out)
        self.assertIn("one-way distance per logged trip", out)
        self.assertIn("Estimated difference", out)

    def test_baseline_difference_for_greener_mode(self):  # SRD 2.1.2, 2.4.3
        out = run_uc1(mode="bus", distance_km=10)
        self.assertIn("Estimated CO2e for this trip: 1050 g", out)
        self.assertIn("Always-drive baseline: 1920 g", out)
        self.assertIn("Estimated difference: 870 g", out)


if __name__ == "__main__":
    unittest.main()
