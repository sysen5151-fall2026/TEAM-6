"""Plan page checks (C.1 Flask pages). Skipped when Flask is not installed.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from unittest import mock

try:
    from src.c1_web_front_end.web_app import create_app
except ImportError:  # Flask is the only non-standard dependency
    create_app = None

from src.c3_data_adapter import reset_confirmed

PLACES = {"origin": "Cornell Arts Quad", "destination": "Ithaca Commons"}


@unittest.skipIf(create_app is None, "Flask not installed")
class TestPlanPage(unittest.TestCase):
    def setUp(self):
        reset_confirmed()
        self.addCleanup(reset_confirmed)
        no_key = mock.patch.dict(os.environ)  # restored on cleanup; tests never call the live ORS
        no_key.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(no_key.stop)
        no_weather = mock.patch("src.c3_data_adapter.weather_adapter._http_json", side_effect=OSError)
        no_weather.start()  # the plan page asks Open-Meteo; tests must not use the network
        self.addCleanup(no_weather.stop)
        self.client = create_app().test_client()

    def test_home_is_the_plan_form_and_both_places_are_required(self):
        page = self.client.get("/").data
        self.assertIn(b"Compare my options", page)
        self.assertIn(b'id="origin" name="origin" type="text" autocomplete="off" required', page)
        self.assertIn(b'id="destination" name="destination" type="text" autocomplete="off" required', page)
        self.assertNotIn(b"One-way distance", page)  # distance is never typed in

    def test_example_links_prefill_the_form(self):
        page = self.client.get("/?origin=Collegetown&destination=Cornell+Arts+Quad").data
        self.assertIn(b'value="Collegetown"', page)
        self.assertIn(b'value="Cornell Arts Quad"', page)

    def test_plan_compares_every_mode_and_recommends_one(self):
        response = self.client.post("/", data=PLACES)
        self.assertEqual(response.status_code, 200)
        for mode in (b"drive", b"walk", b"bike"):
            self.assertIn(mode, response.data)
        self.assertIn(b"estimate", response.data)  # no ORS key in tests: labelled fallback
        self.assertIn(b"Recommended:", response.data)
        self.assertIn(b"Weather was not available", response.data)  # weather mocked as down
        self.assertIn(b"Choose this way", response.data)

    def test_compare_address_still_works(self):
        self.assertEqual(self.client.get("/compare").status_code, 200)
        self.assertIn(b"Recommended:", self.client.post("/compare", data=PLACES).data)

    def test_settings_are_validated_and_applied(self):
        for bad in ({"max_extra_min": "abc"}, {"max_extra_min": "-5"}, {"transit_minutes": "0"}, {"transit_minutes": "x"}):
            with self.subTest(bad=bad):
                response = self.client.post("/", data={**PLACES, **bad})
                self.assertIn(b'role="alert"', response.data)
        both = self.client.post("/", data={**PLACES, "not_feasible_modes": ["walk", "bike"], "transit_minutes": "20"})
        self.assertIn(b"you marked it not feasible", both.data)
        self.assertIn(b"bus", both.data)

    def test_missing_unknown_or_identical_places_show_messages(self):
        cases = (
            {},
            {"origin": "Cornell Arts Quad", "destination": ""},
            {"origin": "   ", "destination": "Collegetown"},
            {"origin": "Cornell Arts Quad", "destination": "nowhere"},
            {"origin": "Collegetown", "destination": "Collegetown"},
        )
        for data in cases:
            with self.subTest(data=data):
                response = self.client.post("/", data=data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'role="alert"', response.data)
                self.assertNotIn(b"Choose this way", response.data)

    def test_places_endpoint_suggests_matching_places(self):
        response = self.client.get("/places?q=upson")
        self.assertEqual(response.status_code, 200)
        found = response.get_json()
        self.assertEqual([p["label"] for p in found], ["Upson Hall"])
        self.assertTrue(42 < found[0]["lat"] < 43 and -77 < found[0]["lon"] < -76)  # coordinates for the map
        self.assertEqual(self.client.get("/places?q=").get_json(), [])
        self.assertEqual(self.client.get("/places").get_json(), [])
        self.assertEqual(self.client.get("/places?q=" + "x" * 5000).status_code, 200)

    def test_page_says_whether_place_search_is_live(self):
        self.assertIn(b"Offline list only", self.client.get("/").data)  # setUp removes the key
        with mock.patch.dict(os.environ, {"ORS_API_KEY": "k"}):
            page = self.client.get("/").data
        self.assertIn(b"Search any place", page)
        self.assertNotIn(b"Offline list only", page)

    def test_finished_plan_hands_both_places_to_the_map(self):
        page = self.client.post("/", data={"origin": "Upson Hall", "destination": "Ithaca Commons"}).data
        self.assertIn(b'"kind": "origin"', page)
        self.assertIn(b'"kind": "destination"', page)
        self.assertIn(b'id="map"', page)
        self.assertIn(b"var planned = [];", self.client.get("/").data)  # nothing to draw before a plan

    def test_route_lines_endpoint_gives_three_modes_with_paths(self):
        reply = self.client.get("/route-lines?olat=42.4436&olon=-76.4838&dlat=42.4396&dlon=-76.4968")
        self.assertEqual(reply.status_code, 200)
        routes = {r["mode"]: r for r in reply.get_json()["routes"]}
        self.assertEqual(set(routes), {"drive", "walk", "bike"})
        for route in routes.values():
            self.assertGreaterEqual(len(route["path"]), 2)
            self.assertTrue(route["estimated"])  # no key in tests: straight-line estimate

    def test_route_lines_endpoint_rejects_bad_or_identical_points(self):
        bad = (
            "/route-lines",
            "/route-lines?olat=abc&olon=1&dlat=2&dlon=3",
            "/route-lines?olat=99&olon=1&dlat=2&dlon=3",
            "/route-lines?olat=nan&olon=1&dlat=2&dlon=3",
            "/route-lines?olat=42.4&olon=-76.4&dlat=42.4&dlon=-76.4",
        )
        for url in bad:
            with self.subTest(url=url):
                reply = self.client.get(url)
                self.assertEqual(reply.status_code, 400)
                self.assertIn("error", reply.get_json())

    def test_map_is_open_by_default_with_location_controls(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="mapcard" hidden', page)
        for needle in ('id="locate"', 'id="usehere"', 'id="legend"', "/route-lines"):
            self.assertIn(needle, page)
        self.assertIn("[hidden] { display:none !important; }", page)  # so hidden buttons and the legend stay hidden

    def test_my_location_can_be_the_start_of_a_plan(self):
        page = self.client.post("/", data={"origin": "My location (42.4440, -76.4830)", "destination": "Ithaca Commons"}).data
        self.assertIn(b"Choose this way", page)


if __name__ == "__main__":
    unittest.main()
