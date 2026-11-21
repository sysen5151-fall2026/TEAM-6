"""Plan-path dispatch and deadline tests (Chapter 11 alternative C, Chapter 12 guardrail for risk TR.16, ADR 0012).

The external calls are replaced by functions that sleep, so no network is used. The failure-path tests make a service
slower than its limit and check that the plan still comes back inside the 3-second display time (requirement 3.4.2.1)
with a labelled fallback, which is what the guardrail is for.

Run:  python -m unittest discover -s tests -t .
"""

import threading
import time
import unittest
from unittest import mock

from src.c2_application_service import plan as plan_module
from src.c3_data_adapter import keepalive, route_adapter
from src.interfaces import ModeComparison, Place, RouteOption, WeatherForecast

START = Place("Cornell Arts Quad", -76.4835, 42.4491, "test")
END = Place("Collegetown", -76.4853, 42.4421, "test")
RAIN = WeatherForecast(precipitation_mm=4.0, forecast_timestamp="t", temperature_c=8.0, wind_kmh=12.0)
ROWS = (ModeComparison("drive", 2.0, 8, 370, 0, "test"), ModeComparison("walk", 1.5, 18, 0, 370, "test"))


def slow(seconds, value):
    def call(*args, **kwargs):
        time.sleep(seconds)
        return value
    return call


def run_plan(route_s, weather_s, dispatch):
    with mock.patch.object(plan_module, "DISPATCH", dispatch), \
         mock.patch.object(plan_module, "geocode", lambda text: START), \
         mock.patch.object(plan_module, "compare_modes", slow(route_s, (ROWS, START, END, []))), \
         mock.patch.object(plan_module, "current_weather", slow(weather_s, RAIN)), \
         mock.patch.object(plan_module, "find_bus", lambda *a: mock.Mock(options=())):
        started = time.perf_counter()
        result = plan_module.plan_commute("a", "b")
        return result, time.perf_counter() - started


class TestDispatch(unittest.TestCase):
    def test_concurrent_dispatch_costs_the_longer_call_not_the_sum(self):
        _, sequential = run_plan(0.4, 0.4, "sequential")
        _, concurrent = run_plan(0.4, 0.4, "concurrent")
        self.assertGreater(sequential, 0.75)
        self.assertLess(concurrent, 0.65)  # about 0.4 s: the weather call ran beside the routes

    def test_both_dispatches_give_the_same_answer(self):
        a, _ = run_plan(0.05, 0.05, "sequential")
        b, _ = run_plan(0.05, 0.05, "concurrent")
        self.assertEqual(a.recommendation, b.recommendation)
        self.assertIn("4 mm precipitation", b.recommendation.weather_note)

    def test_the_selected_dispatch_is_concurrent(self):
        self.assertEqual(plan_module.DISPATCH, "concurrent")


class TestWeatherDeadline(unittest.TestCase):
    """Guardrail for TR.16: a forecast that misses its 1.0 s deadline is dropped, not waited for (requirement 5.4.4)."""

    def test_a_slow_forecast_does_not_hold_the_plan_and_is_labelled(self):
        for dispatch in ("concurrent", "sequential"):
            with self.subTest(dispatch=dispatch):
                result, elapsed = run_plan(0.05, 3.0, dispatch)  # the forecast would take 3 s
                self.assertLess(elapsed, 1.6)
                self.assertEqual(result.recommendation.weather_note,
                                 "Weather was not available, so no weather rules were applied.")
                self.assertTrue(result.recommendation.mode)  # the recommendation is still made

    def test_the_monitoring_counters_record_a_missed_deadline(self):
        before = plan_module.dispatch_stats()
        run_plan(0.05, 3.0, "concurrent")
        run_plan(0.05, 0.05, "concurrent")
        after = plan_module.dispatch_stats()
        self.assertEqual(after["plans"] - before["plans"], 2)
        self.assertEqual(after["weather_missed_deadline"] - before["weather_missed_deadline"], 1)
        self.assertEqual(after["weather_ok"] - before["weather_ok"], 1)

    def test_a_forecast_inside_the_deadline_is_used(self):
        result, _ = run_plan(0.05, 0.2, "concurrent")
        self.assertIn("4 mm precipitation", result.recommendation.weather_note)

    def test_a_failing_forecast_call_is_also_handled(self):
        def broken(*args, **kwargs):
            raise OSError("network is down")

        with mock.patch.object(plan_module, "geocode", lambda text: START), \
             mock.patch.object(plan_module, "compare_modes", lambda *a: (ROWS, START, END, [])), \
             mock.patch.object(plan_module, "current_weather", broken), \
             mock.patch.object(plan_module, "find_bus", lambda *a: mock.Mock(options=())):
            result = plan_module.plan_commute("a", "b")
        self.assertIn("not available", result.recommendation.weather_note)


class TestRouteDeadline(unittest.TestCase):
    def setUp(self):
        route_adapter._route_cache.clear()
        self.addCleanup(route_adapter._route_cache.clear)

    def options(self, ors_route, deadline=0.3):
        with mock.patch.object(route_adapter, "_api_key", lambda: "test-key"), \
             mock.patch.object(route_adapter, "_ors_route", ors_route), \
             mock.patch.object(route_adapter, "ROUTE_DEADLINE_S", deadline), \
             mock.patch.object(route_adapter, "_backend", None):
            started = time.perf_counter()
            result = route_adapter.get_route_options(START, END)
            return result, time.perf_counter() - started

    def test_a_slow_route_service_gets_labelled_estimates_inside_the_deadline(self):
        release = threading.Event()

        def hang(mode, origin, dest):
            release.wait(3.0)
            return RouteOption(mode, 9.9, 99.0, "OpenRouteService", ((0, 0), (1, 1)))

        result, elapsed = self.options(hang)
        release.set()
        self.assertLess(elapsed, 1.0)
        self.assertEqual({o.mode for o in result}, {"drive", "walk", "bike"})
        for option in result:
            self.assertIn("did not answer within 0.3 s", option.source)
            self.assertLess(option.distance_km, 5)  # the estimate, not the late 9.9 km answer
        self.assertEqual(route_adapter._route_cache, {})  # an estimate is never remembered as a routed answer

    def test_one_slow_mode_falls_back_alone(self):
        def mixed(mode, origin, dest):
            if mode == "bike":
                time.sleep(2.0)
            return RouteOption(mode, 1.0, 5.0, "OpenRouteService", ((0, 0), (1, 1)))

        result, elapsed = self.options(mixed)
        self.assertLess(elapsed, 1.0)
        by_mode = {o.mode: o for o in result}
        self.assertEqual(by_mode["drive"].source, "OpenRouteService")
        self.assertIn("did not answer", by_mode["bike"].source)

    def test_fast_routes_are_unchanged_and_remembered(self):
        result, _ = self.options(lambda m, o, d: RouteOption(m, 1.0, 5.0, "OpenRouteService", ((0, 0), (1, 1))))
        self.assertTrue(all(o.source == "OpenRouteService" for o in result))
        self.assertEqual(len(route_adapter._route_cache), 1)


class TestKeepAlive(unittest.TestCase):
    def test_a_failing_tick_never_raises(self):
        with mock.patch.object(route_adapter, "_http_json", side_effect=OSError("down")):
            keepalive.tick()
        self.assertGreaterEqual(keepalive.STATS["failures"], 1)

    def test_a_tick_keeps_as_many_connections_open_as_a_plan_uses_and_sends_no_user_data(self):
        urls = []
        with mock.patch.object(route_adapter, "_api_key", lambda: "k"), \
             mock.patch.object(route_adapter, "_http_json", lambda url, **kw: urls.append(url) or {}):
            keepalive.tick()
        self.assertEqual(len(urls), 1 + len(route_adapter.PROFILES))  # one weather call, one routing call per profile
        weather = [u for u in urls if "api.open-meteo.com" in u]
        self.assertEqual(len(weather), 1)
        self.assertIn("latitude=42.4491", weather[0])  # the fixed campus point only
        self.assertEqual(urls.count(route_adapter.ORS_BASE + "/"), len(route_adapter.PROFILES))

    def test_start_is_idempotent_and_stops(self):
        with mock.patch.object(keepalive, "tick", lambda: None):
            self.assertTrue(keepalive.start(interval_s=0.05))
            self.assertFalse(keepalive.start(interval_s=0.05))
            keepalive.stop()


if __name__ == "__main__":
    unittest.main()
