"""The drive card: alone, or a carpool whose emissions are shared by the people in the car.

Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
from datetime import date
from unittest import mock

try:
    from src.c1_web_front_end.web_app import create_app, parse_share
    from tests.webhelper import make_client, store_of
except ImportError:  # Flask is the only non-standard dependency
    create_app = parse_share = make_client = store_of = None

from src.c2_application_service import campus_goal, confirm_trip, plan_commute
from src.c2_application_service.confirmation import MAX_PEOPLE, MIN_PEOPLE
from src.c3_data_adapter import confirmed_trips, reset_confirmed
from src.interfaces import WeatherForecast

DRY = WeatherForecast(precipitation_mm=0.0, forecast_timestamp="t", temperature_c=15.0, wind_kmh=5.0)
A, B = "Cornell Arts Quad", "Ithaca Commons"


class Base(unittest.TestCase):
    def setUp(self):
        reset_confirmed()
        self.addCleanup(reset_confirmed)
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("ORS_API_KEY", None)
        self.addCleanup(env.stop)
        weather = mock.patch("src.c2_application_service.plan.current_weather", return_value=DRY)
        weather.start()
        self.addCleanup(weather.stop)
        self.today = date.today().isoformat()
        self.drive_g = next(c for c in plan_commute(A, B).comparisons if c.mode == "drive").co2e_g


class TestConfirmCarpool(Base):
    def test_each_person_carries_their_share_of_the_cars_emissions(self):
        for people in (2, 3, 5, 8):
            with self.subTest(people=people):
                reset_confirmed()
                trip, _, errors = confirm_trip(A, B, "carpool", self.today, occupants=people)
                self.assertEqual(errors, [])
                self.assertEqual((trip.mode, trip.occupants), ("carpool", people))
                self.assertEqual(trip.co2e_g, round(self.drive_g / people))
                self.assertEqual(trip.difference_g, self.drive_g - trip.co2e_g)  # against driving alone

    def test_two_people_halve_it_and_driving_alone_is_unchanged(self):
        trip, _, _ = confirm_trip(A, B, "carpool", self.today, occupants=2)
        self.assertEqual(trip.co2e_g, round(self.drive_g / 2))
        reset_confirmed()
        alone, _, _ = confirm_trip(A, B, "drive", self.today)
        self.assertEqual((alone.co2e_g, alone.difference_g, alone.occupants), (self.drive_g, 0, 1))

    def test_the_number_of_people_must_be_between_the_limits(self):
        for people in (-1, 0, 1, MAX_PEOPLE + 1, 100):
            with self.subTest(people=people):
                trip, _, errors = confirm_trip(A, B, "carpool", self.today, occupants=people)
                self.assertIsNone(trip)
                self.assertIn(f"{MIN_PEOPLE} to {MAX_PEOPLE} people", errors[0])
        self.assertEqual(confirmed_trips(), ())

    def test_a_drive_and_a_carpool_of_the_same_trip_do_not_both_count(self):
        confirm_trip(A, B, "drive", self.today)
        trip, _, errors = confirm_trip(A, B, "carpool", self.today, occupants=3)
        self.assertIsNone(trip)
        self.assertIn("already confirmed", errors[0])
        reset_confirmed()
        confirm_trip(A, B, "carpool", self.today, occupants=3)
        trip, _, errors = confirm_trip(A, B, "drive", self.today)
        self.assertIsNone(trip)
        self.assertEqual(len(confirmed_trips()), 1)

    def test_a_carpool_counts_for_the_campus_goal_by_its_share(self):
        before = campus_goal(()).total_g
        confirm_trip(A, B, "carpool", self.today, occupants=4)
        gained = campus_goal(confirmed_trips()).total_g - before
        self.assertEqual(gained, self.drive_g - round(self.drive_g / 4))

    def test_the_other_ways_ignore_the_number_of_people(self):
        trip, _, _ = confirm_trip(A, B, "walk", self.today, occupants=5)
        self.assertEqual(trip.occupants, 1)


@unittest.skipIf(create_app is None, "Flask not installed")
class TestCarpoolOnThePage(Base):
    def setUp(self):
        super().setUp()
        self.client = make_client()
        self.store = store_of(self.client, self)
        self.form = {"origin": A, "destination": B, "date": self.today, "mode": "drive"}

    def plan_page(self):
        return self.client.post("/", data={"origin": A, "destination": B}).get_data(as_text=True)

    def test_the_drive_card_offers_alone_or_a_carpool_with_a_number_of_people(self):
        page = self.plan_page()
        self.assertIn("Who is in the car?", page)
        self.assertIn('name="share" value="alone" checked', page)
        self.assertIn('name="share" value="carpool"', page)
        self.assertIn('id="occupants" name="occupants" type="number" min="2" max="8" step="1" value="2"', page)
        self.assertEqual(page.count('name="share" value="alone"'), 1)  # only the drive card has it
        self.assertIn(f'data-drive-g="{self.drive_g:g}"', page)

    def test_the_page_updates_the_numbers_and_ignores_enter_in_the_people_box(self):
        page = self.plan_page()
        for needle in ("each", "less than driving alone", "Enter 2 to 8 people", '["trip_date", "occupants"]'):
            self.assertIn(needle, page)

    def test_parse_share_reads_the_card(self):
        class Form(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        self.assertEqual(parse_share(Form(mode="drive")), ("drive", 1))
        self.assertEqual(parse_share(Form(mode="drive", share="alone", occupants="4")), ("drive", 1))
        self.assertEqual(parse_share(Form(mode="drive", share="carpool", occupants="4")), ("carpool", 4))
        self.assertEqual(parse_share(Form(mode="drive", share="carpool", occupants="x")), ("carpool", 0))
        self.assertEqual(parse_share(Form(mode="walk", share="carpool", occupants="4")), ("walk", 1))  # only the drive card shares

    def test_choosing_drive_as_a_carpool_records_a_carpool(self):
        response = self.client.post("/confirm", data={**self.form, "share": "carpool", "occupants": "3"})
        self.assertEqual(response.status_code, 302)
        trip = self.store.all()[0]
        self.assertEqual((trip.mode, trip.occupants, trip.co2e_g), ("carpool", 3, round(self.drive_g / 3)))
        done = self.client.get(response.headers["Location"]).get_data(as_text=True)
        self.assertIn("with 3 people", done)
        history = self.client.get("/achievements").get_data(as_text=True)
        self.assertIn("carpool (3 people)", history)

    def test_choosing_drive_alone_records_a_drive(self):
        for extra in ({"share": "alone", "occupants": "5"}, {}):
            with self.subTest(extra=extra):
                self.store.clear()
                self.assertEqual(self.client.post("/confirm", data={**self.form, **extra}).status_code, 302)
                self.assertEqual((self.store.all()[0].mode, self.store.all()[0].occupants), ("drive", 1))

    def test_a_bad_number_of_people_is_a_message_not_a_crash(self):
        for bad in ("", "x", "1", "9", "-3", "2.5", "1e3"):
            with self.subTest(occupants=bad):
                response = self.client.post("/confirm", data={**self.form, "share": "carpool", "occupants": bad})
                self.assertEqual(response.status_code, 200)
                self.assertIn('role="alert"', response.get_data(as_text=True))
        self.assertEqual(self.store.all(), ())

    def test_the_people_count_is_not_used_when_another_way_is_chosen(self):
        response = self.client.post("/confirm", data={**self.form, "mode": "walk", "share": "carpool", "occupants": "x"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.store.all()[0].mode, "walk")


if __name__ == "__main__":
    unittest.main()
