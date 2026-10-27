"""Web entry checks (C.1 Flask page). Skipped when Flask is not installed.

Run:  python -m unittest discover -s tests -t .
"""

import unittest

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


if __name__ == "__main__":
    unittest.main()
