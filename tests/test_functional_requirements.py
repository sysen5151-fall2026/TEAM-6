"""Functional-requirement tests for F.2.2 Manage Reference Data (component specification, document 5).

One test per requirement, named with the requirement identifier and written from the requirement
text (docs/model/EcoCommute_11.3_C8-C9_physical_architecture.xml), not from the code:

    5.4.1 load emission factors      5.4.3 request weather forecast
    5.4.2 select emission factor     5.4.4 resolve trip forecast
    5.5.6 coarse location only (system-wide, flowed down from 3.4.5.2 by equivalence)
    5.5.7 factor resolution 0.001 g/km (system-wide, flowed down from 3.4.6.1 by synthesis)

Run:  python -m unittest discover -s tests -t .
"""

import dataclasses
import os
import unittest

from src.c0_2_reference_data import (
    FactorSetRejected,
    load_emission_factors,
    request_weather_forecast,
    reset_factor_store,
    resolve_trip_forecast,
    select_emission_factor,
    stored_versions,
)
from src.interfaces import CommuteRequest, ForecastQueryContext, WeatherForecast

ROOT = os.path.join(os.path.dirname(__file__), "..")

REVIEWED = {
    "version": "test-2026.1",
    "source": "Test publisher, table 1",
    "units": "g CO2e per vehicle-km",
    "geography": "US",
    "methodology": "tailpipe plus upstream",
    "factors": {"drive": 192.123, "bus": 105.0, "walk": 0.0},
}
ENTRY = CommuteRequest(mode="drive", distance_km=4.0, date="2026-11-09T08:00", coarse_area="Ithaca")


class TestF22FactorFunctions(unittest.TestCase):
    def setUp(self):
        reset_factor_store()

    def test_FR_5_4_1_a_complete_reviewed_set_is_loaded_as_a_versioned_set(self):
        loaded = load_emission_factors(reviewed_factors=REVIEWED)
        self.assertEqual(loaded.version, "test-2026.1")
        self.assertEqual(stored_versions(), ("test-2026.1",))

    def test_FR_5_4_1_a_set_lacking_any_required_attribute_is_rejected_and_not_stored(self):
        for attribute in ("source", "units", "geography", "methodology", "version"):
            with self.subTest(missing=attribute):
                incomplete = {k: v for k, v in REVIEWED.items() if k != attribute}
                with self.assertRaises(FactorSetRejected):
                    load_emission_factors(reviewed_factors=incomplete)
        self.assertEqual(stored_versions(), ())

    def test_FR_5_4_2_the_factor_is_selected_from_the_set_with_its_provenance(self):
        loaded = load_emission_factors(reviewed_factors=REVIEWED)
        factor = select_emission_factor(ENTRY, factor_set=loaded)
        self.assertEqual(factor.g_co2e_per_km, 192.123)
        self.assertEqual(
            (factor.source, factor.units, factor.geography, factor.version),
            ("Test publisher, table 1", "g CO2e per vehicle-km", "US", "test-2026.1"),
        )

    def test_FR_5_4_2_a_factor_is_returned_for_every_mode_the_product_offers(self):
        for mode in ("drive", "carpool", "bus", "bike", "walk", "scooter"):
            factor = select_emission_factor(CommuteRequest(mode, 1.0, "", ""))
            self.assertTrue(factor.version and factor.source, mode)

    def test_FR_5_4_2_without_a_factor_set_the_published_epa_2025_factor_is_returned_with_its_source(self):
        factor = select_emission_factor(ENTRY)
        self.assertEqual((factor.g_co2e_per_km, factor.version, factor.geography), (185.523, "epa-hub-2025-01", "US"))
        self.assertIn("EPA GHG Emission Factors Hub", factor.source)
        self.assertEqual(select_emission_factor(CommuteRequest("bus", 1.0, "", "")).g_co2e_per_km, 41.403)

    def test_FR_5_4_2_a_mode_the_epa_table_lacks_keeps_a_labelled_placeholder(self):
        factor = select_emission_factor(CommuteRequest("scooter", 1.0, "", ""))
        self.assertEqual(factor.version, "stub-0")
        self.assertIn("PLACEHOLDER", factor.source)

    def test_FR_5_5_7_factors_keep_a_resolution_of_at_least_0_001_g_per_km(self):
        loaded = load_emission_factors(reviewed_factors=REVIEWED)
        self.assertEqual(select_emission_factor(ENTRY, factor_set=loaded).g_co2e_per_km, 192.123)
        self.assertEqual(select_emission_factor(ENTRY).g_co2e_per_km, round(select_emission_factor(ENTRY).g_co2e_per_km, 3))


class TestF22WeatherFunctions(unittest.TestCase):
    def test_FR_5_4_3_a_query_is_built_for_the_coarse_location_and_trip_time(self):
        query, context = request_weather_forecast(ENTRY)
        self.assertEqual((query.coarse_area, query.date), ("Ithaca", "2026-11-09T08:00"))
        self.assertEqual((context.coarse_area, context.trip_time), ("Ithaca", "2026-11-09T08:00"))

    def test_FR_5_5_6_the_weather_query_carries_nothing_finer_than_a_coarse_area(self):
        query, _ = request_weather_forecast(ENTRY)
        self.assertEqual({f.name for f in dataclasses.fields(query)}, {"coarse_area", "date"})

    def test_FR_5_4_4_the_forecast_for_the_trip_hour_is_chosen_with_its_timestamp(self):
        hours = tuple(WeatherForecast(0.0, f"2026-11-09T{h:02d}:00") for h in (7, 8, 9))
        _, context = request_weather_forecast(ENTRY)
        trip = resolve_trip_forecast(hours, context=context, response_seconds=0.4)
        self.assertTrue(trip.available)
        self.assertEqual(trip.forecast_timestamp, "2026-11-09T08:00")

    def test_FR_5_4_4_no_response_flags_the_forecast_unavailable(self):
        _, context = request_weather_forecast(ENTRY)
        trip = resolve_trip_forecast(None, context=context)
        self.assertFalse(trip.available)
        self.assertIsNone(trip.forecast)

    def test_FR_5_4_4_a_response_later_than_1_second_flags_the_forecast_unavailable(self):
        _, context = request_weather_forecast(ENTRY)
        late = resolve_trip_forecast(WeatherForecast(0.0, "2026-11-09T08:00"), context=context, response_seconds=1.5)
        self.assertFalse(late.available)
        self.assertEqual(context.timeout_s, 1.0)

    def test_FR_5_4_4_a_series_without_the_trip_hour_flags_the_forecast_unavailable(self):
        context = ForecastQueryContext("Ithaca", "2026-11-09T08:00", 1.0)
        other_hours = (WeatherForecast(0.0, "2026-11-09T10:00"), WeatherForecast(0.0, "2026-11-09T11:00"))
        self.assertFalse(resolve_trip_forecast(other_hours, context=context).available)


class TestF22Contract(unittest.TestCase):
    def test_contract_has_an_operation_for_each_internal_flow_of_f_2_2(self):
        with open(os.path.join(ROOT, "contracts", "api-v1.yaml"), encoding="utf8") as f:
            text = f.read()
        for operation in ("loadEmissionFactors", "selectEmissionFactor", "requestWeatherForecast", "resolveTripForecast"):
            self.assertIn(f"operationId: {operation}", text)


if __name__ == "__main__":
    unittest.main()
