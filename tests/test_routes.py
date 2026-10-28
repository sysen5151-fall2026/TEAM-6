"""Route adapter and mode comparison checks. ORS is always mocked; no network is used.

Run:  python -m unittest discover -s tests -t .
"""

import http.server
import json
import os
import threading
import time
import unittest
import urllib.error
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
        route_adapter.set_cache_backend(None)
        route_adapter._route_cache.clear()  # an answer cached by an earlier test must not stand in for the fallback
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


class TestSuggestionSpeed(unittest.TestCase):
    def setUp(self):
        route_adapter._place_cache.clear()
        route_adapter._suggest_cache.clear()
        for service in route_adapter._paused_until:
            route_adapter._paused_until[service] = 0.0
        self.addCleanup(lambda: [route_adapter._paused_until.__setitem__(k, 0.0) for k in route_adapter._paused_until])
        env = mock.patch.dict(os.environ, ORS_KEY)
        env.start()
        self.addCleanup(env.stop)

    @staticmethod
    def reply(*labels):
        return {"features": [{"geometry": {"coordinates": [-76.5 - i / 100, 42.44]}, "properties": {"label": label}}
                             for i, label in enumerate(labels)]}

    def test_offline_mode_shows_samples_at_once_without_any_request(self):
        with mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError("no request")):
            self.assertEqual([p.label for p in route_adapter.suggest_places("upson", online=False)], ["Upson Hall"])

    def test_the_online_search_waits_for_three_characters_and_uses_a_short_timeout(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=self.reply("Statler Hall, Ithaca, NY, USA")) as http:
            route_adapter.suggest_places("st")
            http.assert_not_called()
            route_adapter.suggest_places("sta")
        self.assertEqual(http.call_count, 1)
        self.assertEqual(http.call_args.kwargs["timeout"], route_adapter.SUGGEST_TIMEOUT_S)

    def test_a_longer_text_reuses_the_answer_for_its_start_without_a_request(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=self.reply(
                "Statler Hall, Ithaca, NY, USA", "Statler Hotel, Ithaca, NY, USA", "State Street, Ithaca, NY, USA")):
            route_adapter.suggest_places("stat")
        with mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError("no request")):
            quick = route_adapter.suggest_places("statl", online=False)
        self.assertEqual([p.label for p in quick], ["Statler Hall, Ithaca, NY, USA", "Statler Hotel, Ithaca, NY, USA"])

    def test_when_both_services_are_out_of_quota_suggestions_pause_and_later_calls_cost_nothing(self):
        quota = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota) as http:
            first = route_adapter.suggest_places("upson")
            self.assertTrue(route_adapter.search_paused())
            second = route_adapter.suggest_places("upson h")
            third = route_adapter.suggest_places("duffield")
        self.assertEqual(http.call_count, 2)  # autocomplete, then search; nothing after that
        self.assertEqual([p.label for p in first], ["Upson Hall"])  # samples still shown
        self.assertEqual([p.label for p in second], ["Upson Hall"])
        self.assertEqual([p.label for p in third], ["Duffield Hall"])

    def test_when_autocomplete_is_out_of_quota_the_search_service_keeps_suggestions_coming(self):
        quota = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        urls = []

        def serve(url, headers=None, body=None, timeout=None):
            urls.append(url.split("?")[0].rsplit("/", 1)[-1])
            if "/geocode/autocomplete" in url:
                raise quota
            return self.reply("Statler Hall, Ithaca, NY, USA")

        with mock.patch.object(route_adapter, "_http_json", side_effect=serve):
            first = route_adapter.suggest_places("statler")
            second = route_adapter.suggest_places("statler h")
        self.assertEqual(urls, ["autocomplete", "search", "search"])  # the second call skipped the paused service
        self.assertEqual([p.label for p in first], ["Statler Hall, Ithaca, NY, USA"])
        self.assertEqual([p.label for p in second], ["Statler Hall, Ithaca, NY, USA"])
        self.assertFalse(route_adapter.search_paused())  # suggestions are not paused: one source still works

    def test_places_are_only_searched_within_the_ithaca_service_area(self):
        urls = []

        def serve(url, headers=None, body=None, timeout=None):
            urls.append(url)
            return self.reply()  # nothing inside the area

        with mock.patch.object(route_adapter, "_http_json", side_effect=serve):
            places = route_adapter.suggest_places("faraway")
        self.assertEqual(len(urls), 1)  # never asked again without the limit
        self.assertIn("boundary.circle.radius=40", urls[0])
        self.assertEqual(places, ())

    def test_a_typed_place_outside_the_area_is_not_found(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=self.reply()) as http:
            self.assertIsNone(route_adapter.geocode("faraway cafe albany"))
        self.assertEqual(http.call_count, 1)
        self.assertIn("boundary.circle.radius=40", http.call_args[0][0])

    def test_a_local_answer_costs_one_request(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=self.reply("Statler Hall, Ithaca, NY, USA")) as http:
            route_adapter.suggest_places("statler")
        self.assertEqual(http.call_count, 1)
        self.assertIn("boundary.circle.lon", http.call_args[0][0])

    def test_typing_a_place_and_not_picking_it_is_looked_up_within_the_area(self):
        urls = []

        def serve(url, headers=None, body=None, timeout=None):
            urls.append(url)
            return self.reply("Statler Hall, Ithaca, NY, USA")

        with mock.patch.object(route_adapter, "_http_json", side_effect=serve):
            place = route_adapter.geocode("statler hall")
        self.assertEqual(place.label, "Statler Hall, Ithaca, NY, USA")
        self.assertEqual(len(urls), 1)
        self.assertIn("boundary.circle.radius", urls[0])

    def test_the_pause_ends_after_the_cooldown(self):
        quota = urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota):
            route_adapter.suggest_places("upson")
        self.assertTrue(route_adapter.search_paused())
        later = route_adapter.time.monotonic() + route_adapter.COOLDOWN_S + 1
        with mock.patch.object(route_adapter.time, "monotonic", return_value=later):
            self.assertFalse(route_adapter.search_paused())
            with mock.patch.object(route_adapter, "_http_json", return_value=self.reply("Upson Hall, Ithaca, NY, USA")) as http:
                route_adapter.suggest_places("upson hall")
        self.assertEqual(http.call_count, 1)  # asking resumed

    def test_other_failures_do_not_pause_anything(self):
        for err in (OSError("down"), urllib.error.HTTPError("u", 500, "Server Error", {}, None), ValueError("bad json")):
            with self.subTest(err=err), mock.patch.object(route_adapter, "_http_json", side_effect=err):
                route_adapter.suggest_places("upson")
                self.assertFalse(route_adapter.search_paused())

    def test_the_services_have_separate_quotas(self):
        quota = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        route_adapter._paused_until["autocomplete"] = route_adapter.time.monotonic() + 60
        reply = {"features": [{"geometry": {"coordinates": [-76.482, 42.4458]}, "properties": {"label": "Statler Hall, Ithaca, NY, USA"}}]}
        with mock.patch.object(route_adapter, "_http_json", return_value=reply):
            self.assertEqual(route_adapter.geocode("statler hall").label, "Statler Hall, Ithaca, NY, USA")  # search still works
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota):
            route_adapter.geocode("another place")  # now search runs out too
        self.assertTrue(route_adapter.search_paused())

    def test_a_quota_answer_on_search_falls_back_to_the_samples_and_pauses_search_only(self):
        quota = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota) as http:
            self.assertIsNone(route_adapter.geocode("somewhere unlisted"))
            self.assertIsNone(route_adapter.geocode("another unlisted place"))
        self.assertEqual(http.call_count, 1)
        self.assertFalse(route_adapter.search_paused())  # autocomplete is a different quota

    def test_a_quota_answer_on_routes_falls_back_to_estimates_without_more_requests(self):
        route_adapter._route_cache.clear()
        quota = urllib.error.HTTPError("u", 429, "Too Many", {}, None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota) as http:
            first = route_adapter.get_route_options(A, B)
            calls_after_first = http.call_count
            c = Place("C", -76.49, 42.45, "test")
            second = route_adapter.get_route_options(A, c)
        self.assertTrue(all("estimate" in o.source for o in first + second))
        self.assertLessEqual(calls_after_first, 3)
        self.assertEqual(http.call_count, calls_after_first)  # the second pair cost no requests


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        code, body, drop = 200, b'{"ok": true}', False
        if self.path.startswith("/forbidden"):
            code, body = 403, b'{"error": "Quota exceeded"}'
        elif self.path.startswith("/notjson"):
            body = b"not json"
        elif self.path.startswith("/headers"):
            body = json.dumps({k.lower(): v for k, v in self.headers.items()}).encode()
        elif self.path.startswith("/drop"):
            drop = True  # answer, then close the socket without saying so
        elif self.path.startswith("/slow"):
            time.sleep(1.0)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        if drop:
            self.close_connection = True

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        reply = json.dumps({"echo": json.loads(body), "auth": self.headers.get("Authorization")}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, *args):
        pass


class _CountingServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    connections = 0

    def get_request(self):
        self.connections += 1
        return super().get_request()

    def handle_error(self, request, client_address):
        pass  # a client that gave up (the timeout test) is not worth a traceback


class TestHttpHelper(unittest.TestCase):
    """The real _http_json against a small local server: no internet needed."""

    @classmethod
    def setUpClass(cls):
        cls.server = _CountingServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self._close_idle()  # forget kept-open connections
        self.addCleanup(self._close_idle)
        self.start = self.server.connections

    @staticmethod
    def _close_idle():
        for waiting in route_adapter._idle.values():
            for conn in waiting:
                conn.close()
        route_adapter._idle.clear()

    def test_one_connection_serves_several_requests(self):
        for _ in range(5):
            self.assertEqual(route_adapter._http_json(self.base + "/ok"), {"ok": True})
        self.assertEqual(self.server.connections - self.start, 1)

    def test_no_accept_header_is_forced_on_the_service(self):
        # the route service answers 406 Not Acceptable to "Accept: application/json" on its GeoJSON endpoint
        sent = route_adapter._http_json(self.base + "/headers")
        self.assertNotIn("accept", sent)
        sent = route_adapter._http_json(self.base + "/headers", headers={"Accept": "application/geo+json"})
        self.assertEqual(sent["accept"], "application/geo+json")  # a caller can still ask for one

    def test_post_sends_the_body_and_headers(self):
        reply = route_adapter._http_json(self.base + "/x", headers={"Authorization": "k"}, body={"coordinates": [[1, 2]]})
        self.assertEqual(reply, {"echo": {"coordinates": [[1, 2]]}, "auth": "k"})

    def test_http_errors_keep_their_status_code(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            route_adapter._http_json(self.base + "/forbidden")
        self.assertEqual(caught.exception.code, 403)
        self.assertIn(b"Quota exceeded", caught.exception.read())
        self.assertEqual(route_adapter._http_json(self.base + "/ok"), {"ok": True})  # the connection still works

    def test_a_reply_that_is_not_json_is_a_value_error(self):
        with self.assertRaises(ValueError):
            route_adapter._http_json(self.base + "/notjson")

    def test_a_connection_the_server_closed_is_replaced_once(self):
        self.assertEqual(route_adapter._http_json(self.base + "/drop"), {"ok": True})
        self.assertEqual(route_adapter._http_json(self.base + "/ok"), {"ok": True})  # retried on a new connection
        self.assertEqual(self.server.connections - self.start, 2)

    def test_a_slow_answer_gives_up_after_the_timeout(self):
        began = time.monotonic()
        with self.assertRaises(OSError):
            route_adapter._http_json(self.base + "/slow", timeout=0.2)
        self.assertLess(time.monotonic() - began, 0.9)  # did not wait for the full second, nor retry

    def test_connections_are_shared_between_threads_like_the_web_server_uses_them(self):
        results = []
        for _ in range(4):  # a new thread per request, as the development server does
            thread = threading.Thread(target=lambda: results.append(route_adapter._http_json(self.base + "/ok")))
            thread.start()
            thread.join()
        self.assertEqual(results, [{"ok": True}] * 4)
        self.assertEqual(self.server.connections - self.start, 1)

    def test_warm_up_opens_a_connection_without_a_key_it_does_nothing(self):
        with mock.patch.object(route_adapter, "ORS_BASE", self.base), mock.patch.dict(os.environ, ORS_KEY):
            route_adapter.warm_up()
            before = self.server.connections
            route_adapter._http_json(self.base + "/ok")
        self.assertEqual(self.server.connections, before)  # the first real request reused the warmed connection
        with mock.patch.dict(os.environ):
            os.environ.pop("ORS_API_KEY", None)
            with mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError("no request")):
                route_adapter.warm_up()

    def test_a_refused_connection_is_an_os_error(self):
        with self.assertRaises(OSError):
            route_adapter._http_json("http://127.0.0.1:9/never", timeout=0.5)


if __name__ == "__main__":
    unittest.main()
