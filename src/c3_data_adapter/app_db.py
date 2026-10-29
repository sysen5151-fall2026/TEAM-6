"""The application's own SQLite file: accounts, invites, trips, and the place and route caches.

One file, `data/app.sqlite` (git-ignored; override with ECOCOMMUTE_DB). It is separate from the
TCAT schedule index, which is rebuilt from the agency's feed. Passwords are stored only as
salted scrypt hashes and invite codes only as SHA-256 hashes, never in the clear.

Connections are cheap, so each caller opens its own (SQLite in WAL mode lets readers and one
writer work side by side). Writes that must not interleave use `transaction`.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.model_trace import realizes

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("ECOCOMMUTE_DB", ROOT / "data" / "app.sqlite"))
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_login INTEGER,
    session_epoch INTEGER NOT NULL DEFAULT 0,  -- raised to sign everyone out (password change, reset)
    prefs TEXT NOT NULL DEFAULT '{}',
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invites (
    id INTEGER PRIMARY KEY,
    code_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL DEFAULT '',
    uses_left INTEGER NOT NULL,
    expires_at INTEGER,
    created_at INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invite_uses (
    invite_id INTEGER NOT NULL REFERENCES invites(id),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tkey TEXT NOT NULL,  -- date, places and way (a drive and a carpool are one car trip)
    date TEXT NOT NULL, mode TEXT NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL,
    distance_km REAL NOT NULL, co2e_g REAL NOT NULL, difference_g REAL NOT NULL,
    recommended_mode TEXT NOT NULL DEFAULT '', occupants INTEGER NOT NULL DEFAULT 1,
    route TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL,
    UNIQUE (user_id, tkey)
);
CREATE TABLE IF NOT EXISTS attempts (  -- sign-ups and log-ins, for the limits
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL, ip TEXT NOT NULL DEFAULT '', username TEXT NOT NULL DEFAULT '',
    ok INTEGER NOT NULL, at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_kind_at ON attempts (kind, at);
CREATE TABLE IF NOT EXISTS place_cache (
    key TEXT PRIMARY KEY, label TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
    source TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS place_cache_lat ON place_cache (lat, lon);
CREATE TABLE IF NOT EXISTS suggest_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS route_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at INTEGER NOT NULL);
"""


class DatabaseError(RuntimeError):
    """The file is from a different version of the application."""


@realizes("UC.4.4")
def connect(path=None, shared: bool = False) -> sqlite3.Connection:
    """Open the database, creating the file and tables the first time.

    shared=True lets several threads use the one connection (the caller must then take a lock).
    """
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    con = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=not shared)  # autocommit; see `transaction`
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 10000")
    con.executescript(SCHEMA)
    row = con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()
    if row is None:
        con.execute("INSERT INTO meta VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
    elif row["value"] != str(SCHEMA_VERSION):
        con.close()
        raise DatabaseError(f"{path} was made by a different version (schema {row['value']}, expected {SCHEMA_VERSION}).")
    if fresh:
        try:
            os.chmod(path, 0o600)  # accounts live here: owner only (a no-op on Windows)
        except OSError:
            pass
    return con


@contextmanager
def transaction(con: sqlite3.Connection):
    """Run the block as one write that nobody else can interleave with; undo it if it raises."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")


def backup(source: sqlite3.Connection, target) -> Path:
    """A consistent copy of the database while it is in use."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    copy = sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
    return target
