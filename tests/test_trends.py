"""Cumulative-difference checks across several trips (SRD 2.1.6).

Run:  python -m unittest discover -s tests -t .
"""

import unittest

from src.c2_application_service import process_commute
from src.c3_data_adapter.data_adapter import reset_store
from src.interfaces import CommuteRequest


def trip(mode, distance_km):
    return CommuteRequest(mode=mode, distance_km=distance_km, date="2026-10-07", coarse_area="Ithaca, NY")


class TestCumulativeDifference(unittest.TestCase):
    def setUp(self):
        reset_store()

    def test_trips_of_different_distance_each_use_their_own_baseline(self):
        process_commute(trip("drive", 10))  # baseline 1920 g, estimate 1920 g, difference 0
        result = process_commute(trip("bike", 2))  # baseline 384 g, estimate 0 g, difference 384
        self.assertEqual(result.trend.cumulative_difference_g, 384)
        self.assertEqual(result.trend.weekly_total_g, 1920)

    def test_difference_accumulates_over_trips(self):
        process_commute(trip("walk", 5))  # 960 g
        result = process_commute(trip("carpool", 4))  # baseline 768 g, estimate 384 g -> 384 g
        self.assertEqual(result.trend.cumulative_difference_g, 960 + 384)

    def test_single_trip_difference_matches_trip_difference(self):
        result = process_commute(trip("bus", 10))
        self.assertEqual(result.trend.cumulative_difference_g, result.estimated_difference_g)


if __name__ == "__main__":
    unittest.main()
