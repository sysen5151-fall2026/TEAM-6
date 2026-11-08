"""A cache of place and route answers that survives restarts, shared by every account.

It saves quota of the online service: a place searched once is never searched again until the
entry is old. Entries hold only the question text (or two known places) and the answer; nothing
says who asked. Every call is guarded: a cache that cannot be read or written is simply skipped,
and the answer is asked for as before.
"""

import json
import sqlite3
import threading
import time

from src.c3_data_adapter import app_db

DAY = 86400
TTL_S = {"suggest": 90 * DAY, "place": 90 * DAY, "route": 30 * DAY}  # place names change slowly; roads a little faster
MAX_ROWS = {"suggest": 20_000, "place": 20_000, "route": 5_000}
TRIM_EVERY = 100  # puts between clean-ups of old and surplus rows
NEAR_DEG = 0.0003  # about 30 m: how close counts as "the same known place"

_TABLE = {"suggest": "suggest_cache", "route": "route_cache", "place": "place_cache"}


class SqliteCache:
    def __init__(self, path, now=time.time):
        self.now = now
        self._lock = threading.Lock()
        self._con = app_db.connect(path, shared=True)
        self._puts = 0

    # ------------------------------------------------------------------ reading
    def get(self, namespace: str, key: str):
        """The stored answer, or None when absent, old or unreadable."""
        table = _TABLE[namespace]
        try:
            with self._lock:
                if namespace == "place":
                    row = self._con.execute("SELECT label, lat, lon, source, created_at FROM place_cache WHERE key = ?", (key,)).fetchone()
                    value = {"label": row["label"], "lat": row["lat"], "lon": row["lon"], "source": row["source"]} if row else None
                else:
                    row = self._con.execute(f"SELECT payload, created_at FROM {table} WHERE key = ?", (key,)).fetchone()
                    value = json.loads(row["payload"]) if row else None
        except (sqlite3.Error, ValueError, TypeError, KeyError):
            return None
        if row is None or self.now() - row["created_at"] > TTL_S[namespace]:
            return None
        return value

    def known_place_near(self, lat: float, lon: float) -> bool:
        """True when a place with these coordinates (within about 30 m) has been looked up before."""
        try:
            with self._lock:
                return self._con.execute(
                    "SELECT 1 FROM place_cache WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? LIMIT 1",
                    (lat - NEAR_DEG, lat + NEAR_DEG, lon - NEAR_DEG, lon + NEAR_DEG)).fetchone() is not None
        except sqlite3.Error:
            return False

    # ------------------------------------------------------------------ writing
    def put(self, namespace: str, key: str, value) -> None:
        table, now = _TABLE[namespace], int(self.now())
        try:
            with self._lock:
                if namespace == "place":
                    self._con.execute("INSERT OR REPLACE INTO place_cache (key, label, lat, lon, source, created_at) VALUES (?,?,?,?,?,?)",
                                      (key, value["label"], value["lat"], value["lon"], value["source"], now))
                else:
                    self._con.execute(f"INSERT OR REPLACE INTO {table} (key, payload, created_at) VALUES (?,?,?)",
                                      (key, json.dumps(value), now))
                self._puts += 1
                if self._puts % TRIM_EVERY == 0:
                    self._trim()
        except (sqlite3.Error, ValueError, TypeError, KeyError):
            pass  # the cache is a convenience; losing a write costs only a repeat request

    def _trim(self) -> None:
        now = int(self.now())
        for namespace, table in _TABLE.items():
            self._con.execute(f"DELETE FROM {table} WHERE created_at < ?", (now - TTL_S[namespace],))
            self._con.execute(
                f"DELETE FROM {table} WHERE key IN (SELECT key FROM {table} ORDER BY created_at DESC LIMIT -1 OFFSET ?)",
                (MAX_ROWS[namespace],))

    def clear(self) -> None:
        with self._lock:
            for table in _TABLE.values():
                self._con.execute(f"DELETE FROM {table}")

    def counts(self) -> dict:
        with self._lock:
            return {ns: self._con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for ns, t in _TABLE.items()}

    def close(self) -> None:
        with self._lock:
            self._con.close()
