"""Web entry checks (C.1 Flask page). Skipped when Flask is not installed.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from unittest import mock

try:
    from src.c1_web_front_end.web_app import create_app
except ImportError:  # Flask is the only non-standard dependency
    create_app = None

from src.c3_data_adapter.data_adapter import reset_store

VALID = {"mode": "drive", "distance_km": "2.5", "date": "2026-10-07", "coarse_area": "Ithaca, NY"}


@unittest.skipIf(create_app is None, "Flask not installed")
class TestWebEntry(unittest.TestCase):
    def setUp(self):
        reset_store()
        no_key = mock.patch.dict(os.environ)  # restored on cleanup; tests never call the live ORS
        no_key.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(no_key.stop)
        no_weather = mock.patch("src.c3_data_adapter.weather_adapter._http_json", side_effect=OSError)
        no_weather.start()  # the compare page asks Open-Meteo; tests must not use the network
        self.addCleanup(no_weather.stop)
        self.client = create_app().test_client()

    def test_form_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculate impact", response.data)

    def test_valid_submission_shows_same_result_as_cli_path(self):
        response = self.client.post("/", data=VALID)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"480 g", response.data)  # 2.5 km x 192 (placeholder), as in the CLI test
        self.assertIn(b"Suggested alternative: walk", response.data)

    def test_infeasible_mode_is_not_recommended(self):  # SRD 2.1.5 through the web path
        response = self.client.post("/", data={**VALID, "not_feasible_modes": "walk"})
        self.assertIn(b"Suggested alternative: bike", response.data)

    def test_bad_input_shows_messages_not_errors(self):
        bad_inputs = (
            {**VALID, "distance_km": "abc"},
            {**VALID, "distance_km": "-3"},
            {**VALID, "distance_km": "nan"},
            {**VALID, "distance_km": "99999"},
            {**VALID, "date": "07/10/2026"},
            {**VALID, "mode": "rocket"},
            {**VALID, "coarse_area": "   "},
        )
        for data in bad_inputs:
            with self.subTest(data=data):
                response = self.client.post("/", data=data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'role="alert"', response.data)
                self.assertNotIn(b"Trip result", response.data)

    def test_empty_post_does_not_crash(self):
        self.assertEqual(self.client.post("/", data={}).status_code, 200)

    def test_compare_page_loads_and_compares_sample_places(self):
        self.assertEqual(self.client.get("/compare").status_code, 200)
        response = self.client.post("/compare", data={"origin": "Cornell Arts Quad", "destination": "Ithaca Commons"})
        self.assertEqual(response.status_code, 200)
        for mode in (b"drive", b"walk", b"bike"):
            self.assertIn(mode, response.data)
        self.assertIn(b"estimate", response.data)  # no ORS key in tests: labelled fallback
        self.assertIn(b"Recommended:", response.data)
        self.assertIn(b"Weather was not available", response.data)  # weather mocked as down

    def test_compare_settings_are_validated_and_applied(self):
        base = {"origin": "Cornell Arts Quad", "destination": "Ithaca Commons"}
        for bad in ({"max_extra_min": "abc"}, {"max_extra_min": "-5"}, {"transit_minutes": "0"}, {"transit_minutes": "x"}):
            with self.subTest(bad=bad):
                response = self.client.post("/compare", data={**base, **bad})
                self.assertIn(b'role="alert"', response.data)
        both = self.client.post("/compare", data={**base, "not_feasible_modes": ["walk", "bike"], "transit_minutes": "20"})
        self.assertIn(b"you marked it not feasible", both.data)
        self.assertIn(b"bus", both.data)

    def test_compare_bad_input_shows_messages(self):
        for data in ({"origin": "Cornell Arts Quad", "destination": "nowhere"}, {}, {"origin": "Collegetown", "destination": "Collegetown"}):
            with self.subTest(data=data):
                response = self.client.post("/compare", data=data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'role="alert"', response.data)


if __name__ == "__main__":
    unittest.main()
