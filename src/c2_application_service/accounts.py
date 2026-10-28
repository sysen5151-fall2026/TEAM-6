"""Accounts: invite-only sign-up, log-in, and the limits that keep both from being abused.

Standard library only. Passwords are hashed with scrypt and a random salt per account; invite
codes are stored as SHA-256 hashes, so a copy of the database reveals neither. Every message
returned to the Commuter is safe to show; none says whether a user name exists on log-in.

The numbers below are PROJECT ASSUMPTIONS for a small invited group (a team, a professor, a TA),
not tuned for the open internet.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import time

from src.c3_data_adapter import app_db

USERNAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
MIN_PASSWORD, MAX_PASSWORD = 6, 128

LOGIN_FAILS_PER_USER = 5
LOGIN_FAILS_PER_IP = 20
LOGIN_WINDOW_S = 15 * 60
DAY, HOUR = 86400, 3600

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1, I
SCRYPT = {"n": 2**15, "r": 8, "p": 1}  # about 70 ms and 32 MB per check


class AccountError(ValueError):
    """Something to tell the Commuter; the text is safe to show."""


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT, maxmem=128 * 1024 * 1024, dklen=32)
    return f"scrypt${SCRYPT['n'].bit_length() - 1}${SCRYPT['r']}${SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """True when the password matches; a damaged or unknown hash never matches."""
    try:
        scheme, log_n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt" or not 10 <= int(log_n) <= 20:
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2 ** int(log_n), r=int(r),
                                p=int(p), maxmem=256 * 1024 * 1024, dklen=len(bytes.fromhex(digest_hex)))
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


_dummy_hash = None


def _burn_time(password: str) -> None:
    """Spend the time of a real check, so an unknown user name answers no faster than a known one."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("no such account")
    verify_password(password, _dummy_hash)


def check_password_rules(password: str, username: str = "") -> None:
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise AccountError(f"The password must be {MIN_PASSWORD} to {MAX_PASSWORD} characters.")
    if username and password.lower() == username.lower():
        raise AccountError("The password must not be the same as the user name.")


def clean_username(raw: str) -> str:
    name = (raw or "").strip().lower()
    if not USERNAME.match(name):
        raise AccountError("The user name must be 3 to 32 letters, digits, dots, dashes or underscores, starting with a letter or digit.")
    return name


# ------------------------------------------------------------------ invites
def _code_hash(code: str) -> str:
    return hashlib.sha256(re.sub(r"[^A-Z0-9]", "", (code or "").upper()).encode()).hexdigest()


def create_invite(db, label: str = "", uses: int = 1, days: float = 14, now=None, code=None) -> str:
    """Make an invite code and return it (a given `code` is used as it is; days=0 means it never expires)."""
    if uses < 1:
        raise ValueError("an invite needs at least one use")
    now = int(now if now is not None else time.time())
    if code is None:
        body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(10))
        code = f"ECO-{body[:5]}-{body[5:]}"
    db.execute("INSERT INTO invites (code_hash, label, uses_left, expires_at, created_at) VALUES (?,?,?,?,?)",
               (_code_hash(code), label.strip()[:60], uses, int(now + days * DAY) if days else None, now))
    return code


def list_invites(db, now=None) -> list:
    now = int(now if now is not None else time.time())
    out = []
    for r in db.execute("SELECT * FROM invites ORDER BY id"):
        state = ("revoked" if r["revoked"] else "used up" if r["uses_left"] < 1 else
                 "expired" if r["expires_at"] and r["expires_at"] <= now else "open")
        out.append({"id": r["id"], "label": r["label"], "uses_left": r["uses_left"], "state": state,
                    "expires_at": r["expires_at"]})
    return out


def revoke_invite(db, invite_id: int) -> bool:
    return db.execute("UPDATE invites SET revoked = 1 WHERE id = ?", (invite_id,)).rowcount == 1


# ------------------------------------------------------------------ limits
def _count(db, kind: str, since: int, ip=None, username=None, ok=None) -> int:
    sql, args = "SELECT COUNT(*) FROM attempts WHERE kind = ? AND at >= ?", [kind, since]
    for column, value in (("ip", ip), ("username", username), ("ok", ok)):
        if value is not None:
            sql += f" AND {column} = ?"
            args.append(value)
    return db.execute(sql, args).fetchone()[0]


def _record(db, kind: str, ip: str, username: str, ok: bool, now: int) -> None:
    db.execute("INSERT INTO attempts (kind, ip, username, ok, at) VALUES (?,?,?,?,?)", (kind, ip, username, int(ok), now))
    db.execute("DELETE FROM attempts WHERE at < ?", (now - 2 * DAY,))  # nothing older than two days is needed


def _wait_text(seconds: int) -> str:
    minutes = max(1, round(seconds / 60))
    return f"{minutes} minute" + ("" if minutes == 1 else "s")


# ------------------------------------------------------------------ sign-up
def register(db, username: str, password: str, invite_code: str, ip: str = "", now=None) -> int:
    """Create an account with a valid invite code. Returns the new user id or raises AccountError."""
    now = int(now if now is not None else time.time())
    name = clean_username(username)
    check_password_rules(password or "", name)

    pw_hash = hash_password(password)  # slow, so done before the write lock is taken
    failure, user_id = "", 0
    with app_db.transaction(db):
        invite = db.execute(
            "SELECT id FROM invites WHERE code_hash = ? AND revoked = 0 AND uses_left > 0 "
            "AND (expires_at IS NULL OR expires_at > ?)", (_code_hash(invite_code), now)).fetchone()
        if invite is None:
            failure = "invite"
        elif db.execute("SELECT 1 FROM users WHERE username = ?", (name,)).fetchone():
            failure = "taken"
        else:
            user_id = db.execute("INSERT INTO users (username, pw_hash, created_at, last_login) VALUES (?,?,?,?)",
                                 (name, pw_hash, now, now)).lastrowid  # signing up signs in
            db.execute("UPDATE invites SET uses_left = uses_left - 1 WHERE id = ?", (invite["id"],))
            db.execute("INSERT INTO invite_uses VALUES (?,?,?)", (invite["id"], user_id, now))
    if failure == "invite":
        raise AccountError("That invite code is not valid, has expired or has been used up.")
    if failure == "taken":
        raise AccountError("That user name is taken.")
    return user_id


def create_user(db, username: str, password: str, demo: bool = False, now=None) -> int:
    """Make an account without an invite (for the manage tool and tests); the same rules otherwise."""
    now = int(now if now is not None else time.time())
    name = clean_username(username)
    check_password_rules(password, name)
    if db.execute("SELECT 1 FROM users WHERE username = ?", (name,)).fetchone():
        raise AccountError("That user name is taken.")
    return db.execute("INSERT INTO users (username, pw_hash, created_at, is_demo) VALUES (?,?,?,?)",
                      (name, hash_password(password), now, int(demo))).lastrowid


# ------------------------------------------------------------------ log-in
def authenticate(db, username: str, password: str, ip: str = "", now=None) -> int:
    """Check a user name and password. Returns the user id or raises AccountError."""
    now = int(now if now is not None else time.time())
    name = (username or "").strip().lower()[:64]
    since = now - LOGIN_WINDOW_S
    for fails, limit in ((_count(db, "login", since, username=name, ok=0), LOGIN_FAILS_PER_USER),
                         (_count(db, "login", since, ip=ip, ok=0), LOGIN_FAILS_PER_IP)):
        if fails >= limit:
            oldest = db.execute("SELECT MIN(at) FROM attempts WHERE kind='login' AND ok=0 AND at >= ?", (since,)).fetchone()[0]
            raise AccountError(f"Too many wrong tries. Wait {_wait_text(int((oldest or now) + LOGIN_WINDOW_S - now))} and try again.")
    row = db.execute("SELECT id, pw_hash FROM users WHERE username = ?", (name,)).fetchone()
    if row is None:
        _burn_time(password or "")
        _record(db, "login", ip, name, False, now)
        raise AccountError("Wrong user name or password.")
    if not verify_password(password or "", row["pw_hash"]):
        _record(db, "login", ip, name, False, now)
        raise AccountError("Wrong user name or password.")
    db.execute("DELETE FROM attempts WHERE kind = 'login' AND username = ? AND ok = 0", (name,))
    db.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, row["id"]))
    return row["id"]


def get_user(db, user_id):
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ------------------------------------------------------------------ changes
def change_password(db, user_id: int, current: str, new: str) -> None:
    """Change the password after checking the current one; every other session is signed out."""
    row = get_user(db, user_id)
    if row is None or not verify_password(current or "", row["pw_hash"]):
        raise AccountError("The current password is not right.")
    check_password_rules(new or "", row["username"])
    db.execute("UPDATE users SET pw_hash = ?, session_epoch = session_epoch + 1 WHERE id = ?", (hash_password(new), user_id))


def set_password(db, username: str, new: str) -> bool:
    """Reset a password (the manage tool). Signs the account out everywhere."""
    name = clean_username(username)
    check_password_rules(new, name)
    return db.execute("UPDATE users SET pw_hash = ?, session_epoch = session_epoch + 1 WHERE username = ?",
                      (hash_password(new), name)).rowcount == 1


def delete_user(db, user_id: int) -> bool:
    """Remove the account and everything that belongs to it."""
    return db.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount == 1


def get_prefs(db, user_id: int) -> dict:
    row = db.execute("SELECT prefs FROM users WHERE id = ?", (user_id,)).fetchone()
    try:
        prefs = json.loads(row["prefs"]) if row else {}
    except ValueError:
        prefs = {}
    return prefs if isinstance(prefs, dict) else {}


def set_pref(db, user_id: int, key: str, value) -> None:
    prefs = get_prefs(db, user_id)
    prefs[key] = value
    db.execute("UPDATE users SET prefs = ? WHERE id = ?", (json.dumps(prefs), user_id))
