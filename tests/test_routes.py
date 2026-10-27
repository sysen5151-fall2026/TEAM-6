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
    """Different distance per profile, as a real routed answer would give (GeoJSON shape)."""
    meters = {"driving-car": 3200, "foot-walking": 1800, "cycling-regular": 2100}
    profile = url.split("/")[-2]  # .../v2/directions/<profile>/geojson
    (lon1, lat1), (lon2, lat2) = body["coordinates"]
    middle = [[(lon1 + lon2) / 2, (lat1 + lat2) / 2 + 0.001]]  # a bend, so it is not a straight line
    return {
        "features": [
            {
                "geometry": {"type": "LineString", "coordinates": [[lon1, lat1]] + middle + [[lon2, lat2]]},
                "properties": {"summary": {"distance": meters[profile], "duration": 600}},
            }
        ]
    }


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
        self.assertEqual([c.mode for c in comparisons], ["drive", "walk", "bike", "scooter"])
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
    def setUp(self):
        route_adapter._route_cache.clear()

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
            if "foot-walking" in url:
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


class TestSuggestions(unittest.TestCase):
    def setUp(self):
        route_adapter._place_cache.clear()
        route_adapter._suggest_cache.clear()

    def test_without_key_sample_places_match_by_words(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("ORS_API_KEY", None)
            labels = [p.label for p in route_adapter.suggest_places("upson")]
            self.assertEqual(labels, ["Upson Hall"])
            self.assertIn("Cornell Gates Hall", [p.label for p in route_adapter.suggest_places("hall cornell")])
            self.assertEqual(route_adapter.suggest_places("u"), ())  # too short to search
            self.assertEqual(route_adapter.suggest_places("zzzz"), ())
            self.assertEqual(route_adapter.geocode("upson hall").label, "Upson Hall")
            self.assertEqual(route_adapter.geocode("upson").label, "Upson Hall")  # unambiguous part
            self.assertIsNone(route_adapter.geocode("hall"))  # several halls: do not guess

    def test_ors_autocomplete_is_merged_deduplicated_and_capped(self):
        reply = {
            "features": [
                {"geometry": {"coordinates": [-76.48 - i / 1000, 42.44]}, "properties": {"label": f"Place {i}, Ithaca"}}
                for i in range(8)
            ]
        }
        reply["features"].insert(
            0, {"geometry": {"coordinates": [-76.4839, 42.4437]}, "properties": {"label": "Upson Hall, Ithaca, NY, USA"}}
        )
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", return_value=reply) as http:
            places = route_adapter.suggest_places("upson")
            route_adapter.suggest_places("upson")  # served from the cache
        self.assertEqual(http.call_count, 1)
        self.assertEqual(len(places), route_adapter.MAX_SUGGESTIONS)
        self.assertEqual(places[0].label, "Upson Hall, Ithaca, NY, USA")  # routed result replaces the sample entry
        self.assertNotIn("Upson Hall", [p.label for p in places])
        self.assertEqual(len({p.label.lower() for p in places}), len(places))
        self.assertIn("focus.point.lon", http.call_args[0][0])  # biased to the campus

    def test_picked_suggestion_resolves_to_the_same_point(self):
        reply = {"features": [{"geometry": {"coordinates": [-76.5, 42.4]}, "properties": {"label": "Odd Cafe, Ithaca, NY"}}]}
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", return_value=reply):
            route_adapter.suggest_places("odd")
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", side_effect=OSError):
            place = route_adapter.geocode("Odd Cafe, Ithaca, NY")  # no network needed
        self.assertEqual((place.lon, place.lat), (-76.5, 42.4))

    def test_ors_failure_keeps_sample_matches(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", side_effect=OSError):
            self.assertEqual([p.label for p in route_adapter.suggest_places("upson")], ["Upson Hall"])
            self.assertEqual(route_adapter.suggest_places("zzzz"), ())
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", return_value={"x": 1}):
            self.assertEqual(route_adapter.suggest_places("qqqq"), ())


class TestRoutePaths(unittest.TestCase):
    def setUp(self):
        route_adapter._route_cache.clear()

    def test_routes_carry_a_path_from_start_to_end_as_lat_lon(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", fake_ors):
            options = route_adapter.get_route_options(A, B)
        for o in options:
            self.assertEqual(o.path[0], (A.lat, A.lon))  # lat first, although ORS sends lon first
            self.assertEqual(o.path[-1], (B.lat, B.lon))
            self.assertEqual(len(o.path), 3)

    def test_fallback_path_is_a_straight_line_between_the_two_places(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("ORS_API_KEY", None)
            for o in route_adapter.get_route_options(A, B):
                self.assertEqual(o.path, ((A.lat, A.lon), (B.lat, B.lon)))

    def test_routed_answers_are_remembered_but_estimates_are_not(self):
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", fake_ors) as http:
            route_adapter.get_route_options(A, B)
            route_adapter.get_route_options(A, B)
        self.assertEqual(len(route_adapter._route_cache), 1)
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", side_effect=OSError):
            route_adapter._route_cache.clear()
            route_adapter.get_route_options(A, B)
        self.assertEqual(route_adapter._route_cache, {})

    def test_second_lookup_makes_no_new_requests(self):
        calls = []

        def counting(url, headers=None, body=None):
            calls.append(url)
            return fake_ors(url, headers, body)

        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", counting):
            route_adapter.get_route_options(A, B)
            route_adapter.get_route_options(A, B)
        self.assertEqual(len(calls), 3)  # one per mode, once

    def test_long_paths_are_thinned_but_keep_both_ends(self):
        points = [(42.0 + i / 10000, -76.0) for i in range(1000)]
        thin = route_adapter._thin(points)
        self.assertLessEqual(len(thin), route_adapter.MAX_PATH_POINTS + 1)
        self.assertEqual((thin[0], thin[-1]), (points[0], points[-1]))
        self.assertEqual(route_adapter._thin(points[:50]), tuple(points[:50]))

    def test_a_route_without_a_line_falls_back(self):
        empty = {"features": [{"geometry": {"coordinates": [[-76.5, 42.4]]}, "properties": {"summary": {"distance": 1, "duration": 1}}}]}
        with mock.patch.dict(os.environ, ORS_KEY), mock.patch.object(route_adapter, "_http_json", return_value=empty):
            self.assertTrue(all("estimate" in o.source for o in route_adapter.get_route_options(A, B)))

    def test_my_location_label_resolves_without_any_service(self):
        with mock.patch.dict(os.environ), mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError):
            os.environ.pop("ORS_API_KEY", None)
            place = route_adapter.geocode("My location (42.4440, -76.4830)")
            self.assertEqual((place.lat, place.lon), (42.444, -76.483))
            self.assertIsNone(route_adapter.geocode("My location (99.0000, -76.4830)"))  # not a real latitude
            self.assertIsNone(route_adapter.geocode("My location (north, west)"))


if __name__ == "__main__":
    unittest.main()
