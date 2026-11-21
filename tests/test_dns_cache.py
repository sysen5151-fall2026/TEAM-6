"""Name cache tests (Chapter 11 alternative D, risk TR.16, ADR 0012). No network is used.

Run:  python -m unittest discover -s tests -t .
"""

import time
import unittest
from unittest import mock

from src.c3_data_adapter import dns_cache, route_adapter


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class TestDnsCache(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.lookups = []
        patches = [mock.patch.object(dns_cache, "_clock", self.clock),
                   mock.patch.object(dns_cache, "_lookup", self.fake_lookup),
                   mock.patch.dict(dns_cache._entries, clear=True),
                   mock.patch.object(dns_cache, "_refreshing", set())]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for key in dns_cache.STATS:
            dns_cache.STATS[key] = 0

    def fake_lookup(self, host, port=443):
        self.lookups.append(host)
        return f"10.0.0.{len(self.lookups)}"

    def test_the_first_lookup_is_made_and_the_next_come_from_the_cache(self):
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.1")
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.1")
        self.assertEqual(self.lookups, ["a.example"])
        self.assertEqual((dns_cache.STATS["misses"], dns_cache.STATS["hits"]), (1, 1))

    def test_a_stale_entry_is_served_at_once_and_refreshed_in_the_background(self):
        dns_cache.resolve("a.example")
        self.clock.now += dns_cache.REFRESH_S + 1
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.1")  # the old address, no wait
        for _ in range(100):  # the refresh thread runs on its own
            if dns_cache.STATS["refreshes"]:
                break
            time.sleep(0.01)
        self.assertEqual(dns_cache.STATS["refreshes"], 1)
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.2")

    def test_an_entry_older_than_the_limit_is_not_served(self):
        dns_cache.resolve("a.example")
        self.clock.now += dns_cache.MAX_AGE_S + 1
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.2")  # a fresh blocking lookup
        self.assertEqual(dns_cache.STATS["misses"], 2)

    def test_a_failed_refresh_keeps_the_old_address_until_it_is_too_old(self):
        dns_cache.resolve("a.example")
        self.clock.now += dns_cache.REFRESH_S + 1
        with mock.patch.object(dns_cache, "_lookup", side_effect=OSError("no dns")):
            self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.1")
            for _ in range(100):
                if dns_cache.STATS["refresh_failures"]:
                    break
                time.sleep(0.01)
        self.assertEqual(dns_cache.STATS["refresh_failures"], 1)
        self.assertEqual(dns_cache.resolve("a.example"), "10.0.0.1")

    def test_a_lookup_that_fails_with_nothing_cached_raises(self):
        with mock.patch.object(dns_cache, "_lookup", side_effect=OSError("no dns")):
            with self.assertRaises(OSError):
                dns_cache.resolve("a.example")

    def test_prefetch_fills_the_cache_for_the_known_hosts(self):
        dns_cache.prefetch(("x.example", "y.example")).join(2)
        self.assertEqual(sorted(self.lookups), ["x.example", "y.example"])


class TestCachedConnection(unittest.TestCase):
    def test_a_connect_to_a_bad_cached_address_forgets_it_and_falls_back(self):
        calls = []

        def fail(*args, **kwargs):
            raise OSError("unreachable")

        conn = route_adapter._CachedHTTPSConnection("api.example", timeout=1)
        with mock.patch.object(dns_cache, "resolve", lambda host, port=443: "192.0.2.1"), \
             mock.patch.object(route_adapter.socket, "create_connection", fail), \
             mock.patch.object(dns_cache, "forget", lambda host: calls.append(("forget", host))), \
             mock.patch.object(route_adapter.http.client.HTTPSConnection, "connect", lambda self: calls.append("ordinary")):
            conn.connect()
        self.assertEqual(calls, [("forget", "api.example"), "ordinary"])

    def test_the_certificate_is_still_checked_for_the_host_name(self):
        seen = {}

        class Context:
            def wrap_socket(self, sock, server_hostname=None):
                seen["hostname"] = server_hostname
                return "wrapped"

        conn = route_adapter._CachedHTTPSConnection("api.example", timeout=1, context=Context())
        with mock.patch.object(dns_cache, "resolve", lambda host, port=443: "192.0.2.1"), \
             mock.patch.object(route_adapter.socket, "create_connection", lambda addr, timeout: ("sock", addr)):
            conn.connect()
        self.assertEqual(seen["hostname"], "api.example")  # the name, not the cached address
        self.assertEqual(conn.sock, "wrapped")

    def test_the_cache_can_be_switched_off(self):
        with mock.patch.object(route_adapter, "USE_DNS_CACHE", False):
            conn = route_adapter._acquire("https", "api.example", 1.0, fresh=True)
        self.assertNotIsInstance(conn, route_adapter._CachedHTTPSConnection)
        with mock.patch.object(route_adapter, "USE_DNS_CACHE", True):
            conn = route_adapter._acquire("https", "api.example", 1.0, fresh=True)
        self.assertIsInstance(conn, route_adapter._CachedHTTPSConnection)


if __name__ == "__main__":
    unittest.main()
