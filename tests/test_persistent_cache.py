"""The cache that remembers places and routes between runs. The online service is always mocked.

"A restart" below means clearing the in-memory caches while the file stays: nothing then in
memory can answer, so only the file can.

Run:  python -m unittest discover -s tests -t .
"""

import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from src.c3_data_adapter import SqliteCache, route_adapter
from src.c3_data_adapter import persistent_cache as pc
from src.interfaces import Place

KEY = {"ORS_API_KEY": "test-key"}
ARTS = Place("Cornell Arts Quad", -76.4835, 42.4491, "sample place list")  # a sample place
COMMONS = Place("Ithaca Commons", -76.4968, 42.4396, "sample place list")
STATLER = {"features": [{"geometry": {"coordinates": [-76.482038, 42.445833]},
                         "properties": {"label": "Statler Hall, Ithaca, NY, USA"}}]}


def restart():
    """Forget everything held in memory, as a new process would."""
    route_adapter._suggest_cache.clear()
    route_adapter._place_cache.clear()
    route_adapter._route_cache.clear()


def routed(url, headers=None, body=None, timeout=None):
    """A routing answer for any profile, with a short line."""
    (lon1, lat1), (lon2, lat2) = body["coordinates"]
    meters = {"driving-car": 3000, "foot-walking": 2000, "cycling-regular": 2200}[url.split("/")[-2]]
    return {"features": [{"geometry": {"coordinates": [[lon1, lat1], [(lon1 + lon2) / 2, (lat1 + lat2) / 2 + 0.001], [lon2, lat2]]},
                          "properties": {"summary": {"distance": meters, "duration": 600}}}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "cache.sqlite"
        self.cache = SqliteCache(self.path)
        self.addCleanup(self.cache.close)
        restart()
        route_adapter.set_cache_backend(self.cache)
        self.addCleanup(route_adapter.set_cache_backend, None)
        self.addCleanup(restart)
        for service in route_adapter._paused_until:
            route_adapter._paused_until[service] = 0.0
        env = mock.patch.dict(os.environ, KEY)
        env.start()
        self.addCleanup(env.stop)


class TestSuggestions(Base):
    def test_a_search_made_once_is_not_made_again_even_after_a_restart(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER) as http:
            first = route_adapter.suggest_places("statler")
            self.assertEqual(http.call_count, 1)
            restart()
            second = route_adapter.suggest_places("statler")
            self.assertEqual(http.call_count, 1)  # answered from the file
        self.assertEqual([(p.label, p.lat, p.lon) for p in first], [(p.label, p.lat, p.lon) for p in second])
        self.assertEqual(second[0].source, "OpenRouteService geocoder")

    def test_it_works_across_two_separate_cache_objects_on_one_file(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            route_adapter.suggest_places("statler")
        restart()
        route_adapter.set_cache_backend(SqliteCache(self.path))  # a new process opening the same file
        with mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError("no request expected")):
            self.assertEqual(route_adapter.suggest_places("statler")[0].label, "Statler Hall, Ithaca, NY, USA")

    def test_a_failed_request_is_not_cached(self):
        with mock.patch.object(route_adapter, "_http_json", side_effect=OSError("down")):
            route_adapter.suggest_places("statler")
        self.assertEqual(self.cache.counts()["suggest"], 0)
        quota = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=quota):
            route_adapter.suggest_places("statler hall")
        self.assertEqual(self.cache.counts()["suggest"], 0)

    def test_an_answer_with_no_places_is_cached_too(self):
        with mock.patch.object(route_adapter, "_http_json", return_value={"features": []}) as http:
            route_adapter.suggest_places("zzzzqq")
            restart()
            self.assertEqual(route_adapter.suggest_places("zzzzqq"), ())
        self.assertEqual(http.call_count, 1)  # asked once; nothing more after the restart

    def test_an_old_entry_is_asked_for_again(self):
        clock = [1_800_000_000]
        self.cache.now = lambda: clock[0]
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER) as http:
            route_adapter.suggest_places("statler")
            restart()
            clock[0] += pc.TTL_S["suggest"] - 10
            route_adapter.suggest_places("statler")
            self.assertEqual(http.call_count, 1)  # still fresh
            restart()
            clock[0] += 20
            route_adapter.suggest_places("statler")
            self.assertEqual(http.call_count, 2)  # now too old

    def test_a_damaged_entry_is_ignored(self):
        self.cache._con.execute("INSERT INTO suggest_cache VALUES ('statler', 'not json {', ?)", (int(self.cache.now()),))
        self.cache._con.execute("INSERT INTO suggest_cache VALUES ('statler h', '{\"places\": [{\"label\": 1}]}', ?)", (int(self.cache.now()),))
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER) as http:
            self.assertEqual(route_adapter.suggest_places("statler")[0].label, "Statler Hall, Ithaca, NY, USA")
            route_adapter.suggest_places("statler h")
        self.assertEqual(http.call_count, 2)  # both fell back to asking


class TestPlaces(Base):
    def test_a_picked_suggestion_still_resolves_to_the_same_point_after_a_restart(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            picked = route_adapter.suggest_places("statler")[0]
        restart()
        with mock.patch.object(route_adapter, "_http_json", side_effect=AssertionError("no request expected")):
            again = route_adapter.geocode(picked.label)
        self.assertEqual((again.lat, again.lon), (picked.lat, picked.lon))

    def test_typed_text_that_was_looked_up_once_is_not_looked_up_again(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER) as http:
            one = route_adapter.geocode("statler hall")
            restart()
            two = route_adapter.geocode("Statler  Hall")  # spaces and case do not matter
        self.assertEqual(http.call_count, 1)
        self.assertEqual((one.lat, one.lon), (two.lat, two.lon))

    def test_a_looked_up_place_becomes_a_known_place(self):
        self.assertFalse(self.cache.known_place_near(42.445833, -76.482038))
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            route_adapter.geocode("statler hall")
        self.assertTrue(self.cache.known_place_near(42.445833, -76.482038))
        self.assertTrue(self.cache.known_place_near(42.4459, -76.4821))  # within about 30 m
        self.assertFalse(self.cache.known_place_near(42.4500, -76.4900))


class TestRoutes(Base):
    def test_routes_between_known_places_are_kept_between_runs(self):
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed) as http:
            first = route_adapter.get_route_options(ARTS, COMMONS)
            self.assertEqual(http.call_count, 3)
            restart()
            second = route_adapter.get_route_options(ARTS, COMMONS)
            self.assertEqual(http.call_count, 3)  # the second time cost nothing
        self.assertEqual(first, second)  # distances, times and the whole line come back unchanged
        self.assertTrue(all(len(o.path) >= 3 for o in second))

    def test_a_position_that_is_not_a_known_place_is_never_kept(self):
        mine = Place("My location (42.4600, -76.4700)", -76.4700, 42.4600, "your device location")  # nowhere that is a known place
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed):
            route_adapter.get_route_options(mine, COMMONS)
        self.assertEqual(self.cache.counts()["route"], 0)
        elsewhere = Place("x", -76.45, 42.47, "map")
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed):
            route_adapter.get_route_options(ARTS, elsewhere)
        self.assertEqual(self.cache.counts()["route"], 0)

    def test_places_found_by_search_count_as_known(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            statler = route_adapter.geocode("statler hall")
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed):
            route_adapter.get_route_options(ARTS, statler)
        self.assertEqual(self.cache.counts()["route"], 1)

    def test_routes_with_any_estimated_mode_are_not_kept(self):
        def partly(url, headers=None, body=None, timeout=None):
            if "foot-walking" in url:
                raise OSError("down")
            return routed(url, headers, body)

        with mock.patch.object(route_adapter, "_http_json", side_effect=partly):
            route_adapter.get_route_options(ARTS, COMMONS)
        self.assertEqual(self.cache.counts()["route"], 0)  # a guess must never be remembered as a fact

    def test_a_stored_route_set_that_is_incomplete_or_estimated_is_not_trusted(self):
        key = "|".join(f"{v:.4f}" for v in (ARTS.lat, ARTS.lon, COMMONS.lat, COMMONS.lon))
        self.cache.put("route", key, {"routes": [{"mode": "drive", "distance_km": 1, "duration_min": 1, "source": "OpenRouteService", "path": [[1, 2]]}]})
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed) as http:
            route_adapter.get_route_options(ARTS, COMMONS)
        self.assertEqual(http.call_count, 3)

    def test_a_damaged_route_entry_is_ignored(self):
        key = "|".join(f"{v:.4f}" for v in (ARTS.lat, ARTS.lon, COMMONS.lat, COMMONS.lon))
        self.cache._con.execute("INSERT INTO route_cache VALUES (?, 'garbage', ?)", (key, int(self.cache.now())))
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed) as http:
            self.assertEqual(len(route_adapter.get_route_options(ARTS, COMMONS)), 3)
        self.assertEqual(http.call_count, 3)

    def test_no_backend_means_memory_only_as_before(self):
        route_adapter.set_cache_backend(None)
        with mock.patch.object(route_adapter, "_http_json", side_effect=routed) as http:
            route_adapter.get_route_options(ARTS, COMMONS)
            restart()
            route_adapter.get_route_options(ARTS, COMMONS)
        self.assertEqual(http.call_count, 6)


class TestTheCacheItself(Base):
    def test_it_keeps_only_questions_and_answers_never_who_asked(self):
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            route_adapter.suggest_places("statler")
        for table in ("suggest_cache", "route_cache", "place_cache"):
            columns = {r["name"] for r in self.cache._con.execute(f"PRAGMA table_info({table})")}
            self.assertFalse(columns & {"user_id", "username", "ip", "user", "session"}, table)

    def test_surplus_and_old_rows_are_trimmed_now_and_then(self):
        with mock.patch.dict(pc.MAX_ROWS, {"suggest": 5}), mock.patch.object(pc, "TRIM_EVERY", 10):
            clock = [1_800_000_000]
            self.cache.now = lambda: clock[0]
            for i in range(10):
                clock[0] += 1
                self.cache.put("suggest", f"q{i}", {"places": []})
            self.assertEqual(self.cache.counts()["suggest"], 5)
            self.assertIsNone(self.cache.get("suggest", "q0"))  # the oldest went
            self.assertIsNotNone(self.cache.get("suggest", "q9"))

    def test_old_rows_are_removed_when_trimming(self):
        clock = [1_800_000_000]
        self.cache.now = lambda: clock[0]
        with mock.patch.object(pc, "TRIM_EVERY", 2):
            self.cache.put("route", "old", {"routes": []})
            clock[0] += pc.TTL_S["route"] + 100
            self.cache.put("route", "new", {"routes": []})
        self.assertEqual(self.cache.counts()["route"], 1)

    def test_a_broken_database_never_breaks_a_lookup(self):
        self.cache._con.execute("DROP TABLE suggest_cache")
        with mock.patch.object(route_adapter, "_http_json", return_value=STATLER):
            self.assertEqual(route_adapter.suggest_places("statler")[0].label, "Statler Hall, Ithaca, NY, USA")
        self.assertFalse(sqlite3.connect(self.path).execute("SELECT 1").fetchone() is None)

    def test_many_threads_can_use_it_at_once(self):
        errors = []

        def work(n):
            try:
                for i in range(40):
                    self.cache.put("suggest", f"{n}-{i}", {"places": []})
                    self.cache.get("suggest", f"{n}-{i}")
                    self.cache.known_place_near(42.4, -76.4)
            except Exception as err:  # noqa: BLE001
                errors.append(err)

        threads = [threading.Thread(target=work, args=(n,)) for n in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.cache.counts()["suggest"], 240)

    def test_clear_empties_everything(self):
        self.cache.put("suggest", "a", {"places": []})
        self.cache.put("place", "b", {"label": "B", "lat": 1, "lon": 2, "source": "s"})
        self.cache.clear()
        self.assertEqual(self.cache.counts(), {"suggest": 0, "route": 0, "place": 0})


if __name__ == "__main__":
    unittest.main()
