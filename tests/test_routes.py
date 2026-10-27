"""Route adapter and mode comparison checks. ORS is always mocked; no network is used.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from unittest import mock

from src.c2_application_service import compare_modes
from src.c3_data_adapter import route_adapter
from src.interfaces import Place

A = Place("A", -76.4835, 42.4491, "test")
B = Place("B", -76.4968, 42.4396, "test")
ORS_KEY = {"ORS_API_KEY": "test-key"}


def fake_ors(url, headers=None, body=None):
    """Different distance per profile, as a real routed answer would give."""
    meters = {"driving-car": 3200, "foot-walking": 1800, "cycling-regular": 2100}
    profile = url.rsplit("/", 1)[-1]
    return {"routes": [{"summary": {"distance": meters[profile], "duration": 600}}]}


class TestFallbackWithoutKey(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(patcher.stop)

    def test_sample_places_resolve_and_unknown_text_does_not(self):
        self.assertEqual(route_adapter.geocode("collegetown").label, "Collegetown")
        self.assertIsNone(route_adapter.geocode("somewhere unlisted"))
        self.assertIsNone(route_adapter.geocode("   "))

    def test_fallback_gives_all_three_modes_labelled_as_estimates(self):
        options = route_adapter.get_route_options(A, B)
        self.assertEqual({o.mode for o in options}, {"drive", "walk", "bike"})
        for o in options:
            self.assertGreater(o.distance_km, 0)
            self.assertIn("estimate", o.source)

    def test_compare_modes_with_sample_places(self):
        comparisons, origin, dest, errors = compare_modes("Cornell Arts Quad", "Ithaca Commons")
        self.assertEqual(errors, [])
        self.assertEqual(len(comparisons), 3)
        drive = next(c for c in comparisons if c.mode == "drive")
        self.assertEqual(drive.difference_g, 0)  # baseline is the drive route itself

    def test_unknown_place_returns_errors_not_exceptions(self):
        comparisons, _, _, errors = compare_modes("Cornell Arts Quad", "nowhere")
        self.assertEqual(comparisons, ())
        self.assertEqual(len(errors), 1)

    def test_same_place_is_rejected(self):
        comparisons, _, _, errors = compare_modes("Collegetown", "Collegetown")
        self.assertEqual(comparisons, ())
        self.assertIn("same place", errors[0])


class TestWithMockedOrs(unittest.TestCase):
    def test_each_mode_keeps_its_own_routed_distance(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", fake_ors):
            options = {o.mode: o for o in route_adapter.get_route_options(A, B)}
        self.assertEqual(options["drive"].distance_km, 3.2)
        self.assertEqual(options["walk"].distance_km, 1.8)  # not the drive distance
        self.assertEqual(options["bike"].distance_km, 2.1)
        self.assertEqual(options["drive"].duration_min, 10.0)
        self.assertEqual(options["drive"].source, "OpenRouteService")

    def test_baseline_uses_drive_route_distance(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", fake_ors):
            comparisons, _, _, errors = compare_modes("Cornell Arts Quad", "Ithaca Commons")
        self.assertEqual(errors, [])
        walk = next(c for c in comparisons if c.mode == "walk")
        self.assertEqual(walk.co2e_g, 0)
        self.assertEqual(walk.difference_g, round(3.2 * 192))  # drive 3.2 km x placeholder 192 g/km

    def test_failed_mode_falls_back_alone(self):
        def flaky(url, headers=None, body=None):
            if url.endswith("foot-walking"):
                raise OSError("down")
            return fake_ors(url, headers, body)

        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", flaky):
            options = {o.mode: o for o in route_adapter.get_route_options(A, B)}
        self.assertEqual(options["drive"].source, "OpenRouteService")
        self.assertIn("estimate", options["walk"].source)

    def test_malformed_response_falls_back(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(
            route_adapter, "_http_json", return_value={"unexpected": True}
        ):
            options = route_adapter.get_route_options(A, B)
        self.assertTrue(all("estimate" in o.source for o in options))

    def test_geocode_reads_lon_lat_order(self):
        reply = {"features": [{"geometry": {"coordinates": [-76.5, 42.44]}, "properties": {"label": "X, Ithaca"}}]}
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", return_value=reply):
            place = route_adapter.geocode("X")
        self.assertEqual((place.lon, place.lat, place.label), (-76.5, 42.44, "X, Ithaca"))

    def test_geocode_network_failure_returns_none(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", side_effect=OSError):
            self.assertIsNone(route_adapter.geocode("X"))


if __name__ == "__main__":
    unittest.main()
