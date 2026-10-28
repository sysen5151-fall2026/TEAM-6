"""Look after the accounts from the command line (there is deliberately no admin web page).

    python -m src.manage seed                                  # accounts + invite codes from data/roster.json
    python -m src.manage create-invite --label Karen          # prints a code once; give it to her
    python -m src.manage create-invite --label class --uses 5 --days 7
    python -m src.manage invites                               # which codes are open, used up, expired
    python -m src.manage create-user prof --generate --with-sample-trips   # a demo account, password printed once
    python -m src.manage users
    python -m src.manage set-password alice                    # asks for the new password; signs alice out everywhere
    python -m src.manage delete-user alice
    python -m src.manage backup                                # a consistent copy in data/backups/
    python -m src.manage cache-stats | clear-cache

Passwords are never accepted on the command line (they would stay in the shell history).
"""

import argparse
import getpass
import json
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path

from src.c2_application_service import accounts, load_demo_trips
from src.c2_application_service.accounts import AccountError
from src.c3_data_adapter import SqliteCache, SqliteTrips, app_db

PASSWORD_ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters


def _when(ts) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "never"


def _ask_password(prompt="New password: ") -> str:
    first = getpass.getpass(prompt)
    if first != getpass.getpass("Again: "):
        raise AccountError("The two passwords were not the same.")
    return first


def _password(args) -> tuple:
    """(password, was_generated)."""
    if args.generate:
        return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(16)), True
    return _ask_password(), False


def seed(db, path: Path, out=print) -> int:
    """Create the accounts and the few invite codes listed in a private JSON file (kept out of git).

    {"invites": [{"label": "team", "code": "TEAM6-ABCD"}],
     "users": [{"username": "karen", "password": "karenli#", "demo": false, "sample_trips": false}]}

    Safe to run again: a name or code that already exists is left as it is.
    """
    if not path.exists():
        out(f"No roster file at {path}. Make it as described in the README (it must stay out of git).")
        return 1
    roster = json.loads(path.read_text(encoding="utf-8"))
    known = {r["code_hash"] for r in db.execute("SELECT code_hash FROM invites")}
    for item in roster.get("invites", []):
        if accounts._code_hash(item["code"]) in known:
            out(f"Invite '{item['label']}' already exists.")
            continue
        accounts.create_invite(db, item["label"], uses=item.get("uses", 1000), days=0, code=item["code"])
        out(f"Invite '{item['label']}' created (works for up to {item.get('uses', 1000)} accounts, never expires).")
    for item in roster.get("users", []):
        name = accounts.clean_username(item["username"])
        if db.execute("SELECT 1 FROM users WHERE username = ?", (name,)).fetchone():
            out(f"Account '{name}' already exists.")
            continue
        demo = bool(item.get("demo") or item.get("sample_trips"))
        user_id = accounts.create_user(db, name, item["password"], demo=demo)
        extra = f", {load_demo_trips(SqliteTrips(db, user_id))} sample trips" if item.get("sample_trips") else ""
        out(f"Account '{name}' created{extra}.")
    return 0


def run(args, db, out=print) -> int:
    cmd = args.command
    if cmd == "create-invite":
        code = accounts.create_invite(db, args.label, args.uses, args.days)
        out(f"Invite code: {code}")
        out(f"  for: {args.label or '(no label)'} | uses: {args.uses} | valid for {args.days:g} days")
        out("  This is the only time the code is shown. Send it privately.")
    elif cmd == "seed":
        return seed(db, Path(args.file), out)
    elif cmd == "invites":
        rows = accounts.list_invites(db)
        for r in rows:
            out(f"#{r['id']:<3} {r['state']:<8} uses left {r['uses_left']:<3} expires {_when(r['expires_at']):<17} {r['label']}")
        if not rows:
            out("No invite codes yet. Make one with: python -m src.manage create-invite")
    elif cmd == "revoke-invite":
        revoked = accounts.revoke_invite(db, args.id)
        out("Revoked." if revoked else "No such invite.")
        return 0 if revoked else 1
    elif cmd == "create-user":
        password, generated = _password(args)
        user_id = accounts.create_user(db, args.username, password, demo=args.demo or args.with_sample_trips)
        out(f"Created account '{accounts.clean_username(args.username)}'.")
        if generated:
            out(f"  Password (shown once): {password}")
        if args.with_sample_trips:
            out(f"  Loaded {load_demo_trips(SqliteTrips(db, user_id))} sample trips (labelled as samples on the pages).")
    elif cmd == "users":
        rows = db.execute("SELECT u.id, u.username, u.created_at, u.last_login, u.is_demo, "
                          "(SELECT COUNT(*) FROM trips t WHERE t.user_id = u.id) AS trips FROM users u ORDER BY u.id").fetchall()
        for r in rows:
            out(f"#{r['id']:<3} {r['username']:<20} created {_when(r['created_at']):<17} last login {_when(r['last_login']):<17} "
                f"{r['trips']:>3} trips{'  (demo)' if r['is_demo'] else ''}")
        if not rows:
            out("No accounts yet.")
    elif cmd == "set-password":
        password, generated = _password(args)
        if not accounts.set_password(db, args.username, password):
            out("No such account.")
            return 1
        out("Password changed; every browser signed in as that account was signed out.")
        if generated:
            out(f"  Password (shown once): {password}")
    elif cmd == "delete-user":
        row = db.execute("SELECT id FROM users WHERE username = ?", (accounts.clean_username(args.username),)).fetchone()
        if row is None:
            out("No such account.")
            return 1
        if not args.yes and input(f"Delete '{args.username}' and all their trips? Type yes: ").strip().lower() != "yes":
            out("Not deleted.")
            return 1
        accounts.delete_user(db, row["id"])
        out("Deleted.")
    elif cmd == "backup":
        target = Path(args.path) if args.path else app_db.DB_PATH.parent / "backups" / f"app-{time.strftime('%Y%m%d-%H%M%S')}.sqlite"
        out(f"Backup written to {app_db.backup(db, target)}")
    elif cmd == "cache-stats":
        cache = SqliteCache(args.db or app_db.DB_PATH)
        out("Cached answers: " + ", ".join(f"{k} {v}" for k, v in cache.counts().items()))
        cache.close()
    elif cmd == "clear-cache":
        cache = SqliteCache(args.db or app_db.DB_PATH)
        cache.clear()
        cache.close()
        out("Cache cleared.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.manage", description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", help="database file (default data/app.sqlite)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-invite", help="make an invite code")
    p.add_argument("--label", default="", help="who it is for")
    p.add_argument("--uses", type=int, default=1, help="how many accounts it can make (default 1)")
    p.add_argument("--days", type=float, default=14, help="how long it works (default 14)")
    p = sub.add_parser("seed", help="create the accounts and invite codes listed in a private roster file")
    p.add_argument("--file", default="data/roster.json", help="default data/roster.json (git-ignored)")
    sub.add_parser("invites", help="list invite codes (never their text)")
    p = sub.add_parser("revoke-invite", help="stop an invite code from working")
    p.add_argument("id", type=int)
    p = sub.add_parser("create-user", help="make an account without an invite")
    p.add_argument("username")
    p.add_argument("--generate", action="store_true", help="make a random password and print it once")
    p.add_argument("--demo", action="store_true", help="mark it as a demo account")
    p.add_argument("--with-sample-trips", action="store_true", help="fill it with labelled sample trips")
    sub.add_parser("users", help="list accounts")
    p = sub.add_parser("set-password", help="reset a password")
    p.add_argument("username")
    p.add_argument("--generate", action="store_true")
    p = sub.add_parser("delete-user", help="delete an account and its trips")
    p.add_argument("username")
    p.add_argument("--yes", action="store_true", help="do not ask")
    p = sub.add_parser("backup", help="copy the database")
    p.add_argument("path", nargs="?")
    sub.add_parser("cache-stats", help="how many place and route answers are kept")
    sub.add_parser("clear-cache", help="forget the kept place and route answers")
    return parser


def main(argv=None, out=print) -> int:
    args = build_parser().parse_args(argv)
    db = app_db.connect(args.db) if args.db else app_db.connect()
    try:
        return run(args, db, out)
    except AccountError as err:
        out(f"Not done: {err}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
