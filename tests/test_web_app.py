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
        for mode in (b"drive", b"walk"):
            self.assertIn(mode, response.data)
        self.assertIn(b"estimate", response.data)  # no ORS key in tests: labelled fallback
        self.assertIn(b"Recommended:", response.data)
        self.assertIn(b"Weather was not available", response.data)  # weather mocked as down
        self.assertIn(b"Choose this way", response.data)

    def test_compare_address_still_works(self):
        self.assertEqual(self.client.get("/compare").status_code, 200)
        self.assertIn(b"Recommended:", self.client.post("/compare", data=PLACES).data)

    def test_the_student_has_no_bike_unless_ticked(self):
        page = self.client.post("/", data=PLACES).get_data(as_text=True)
        self.assertIn('name="mode" value="walk"', page)
        self.assertNotIn('name="mode" value="bike"', page)
        self.assertNotIn('name="mode" value="scooter"', page)
        self.assertIn("Have a bike or a scooter?", page)
        both = self.client.post("/", data={**PLACES, "have": ["bike", "scooter"]}).get_data(as_text=True)
        self.assertIn('name="mode" value="bike"', both)
        self.assertIn('name="mode" value="scooter"', both)
        self.assertNotIn("Have a bike or a scooter?", both)
        one = self.client.post("/", data={**PLACES, "have": ["scooter"]}).get_data(as_text=True)
        self.assertIn("Have a bike? Tick it", one)  # only what is still missing is mentioned
        self.assertIn("The scooter is assumed to use the bike route and speed.", one)
        self.assertNotIn("; the scooter is assumed", one)  # said once, not mixed into the route sources

    def test_ticked_vehicles_are_kept_for_the_confirm_step_and_junk_is_dropped(self):
        page = self.client.post("/", data={**PLACES, "have": ["scooter", "rocket"]}).get_data(as_text=True)
        self.assertIn('<input type="hidden" name="have" value="scooter">', page)
        self.assertNotIn('name="have" value="rocket"', page)
        self.assertNotIn('<input type="hidden" name="have" value="rocket">', page)

    def test_the_old_limit_boxes_are_gone_and_the_ride_box_replaces_them(self):
        page = self.client.get("/").get_data(as_text=True)
        for gone in ("max_extra_min", "transit_minutes", "not_feasible_modes", "Bus door-to-door", "My limits", "Try:"):
            self.assertNotIn(gone, page)
        self.assertIn("What I have with me", page)
        self.assertIn('name="have" value="bike"', page)
        self.assertIn('name="have" value="scooter"', page)
        self.assertNotRegex(page, r'name="have" value="(bike|scooter)"\s+checked')  # nothing ticked by default

    def test_a_bus_card_is_reserved_but_cannot_be_chosen(self):
        page = self.client.post("/", data=PLACES).get_data(as_text=True)
        self.assertIn("Coming soon", page)
        self.assertIn("Not available yet", page)
        self.assertNotIn('name="mode" value="bus"', page)

    def test_start_from_my_location_sits_under_the_from_box(self):
        page = self.client.get("/").get_data(as_text=True)
        from_box = page.index('id="origin"')
        button = page.index('id="usehere"')
        to_box = page.index('id="destination"')
        self.assertTrue(from_box < button < to_box)  # right after From, before To
        self.assertLess(page.index('id="usehere"'), page.index('id="mapcard"'))  # not in the map card

    def test_the_date_is_asked_where_the_way_is_chosen(self):
        self.assertNotIn('id="trip_date"', self.client.get("/").get_data(as_text=True))
        page = self.client.post("/", data=PLACES).get_data(as_text=True)
        self.assertIn('id="trip_date"', page)
        self.assertIn("max=", page)

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
        self.assertNotIn(b"Offline list only", page)  # nothing to warn about when search is live

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
