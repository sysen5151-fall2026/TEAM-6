"""Start the web entry.

    python -m src.main_web                       # this computer only: http://127.0.0.1:5000
    python -m src.main_web --host 0.0.0.0        # reachable from other devices (read README first)
    python -m src.main_web --port 8080

Accounts, invites and the place and route cache live in data/app.sqlite (override: ECOCOMMUTE_DB).
Make invite codes and demo accounts with `python -m src.manage`.
"""

import argparse
import threading

from src.c1_web_front_end.web_app import create_app
from src.c3_data_adapter import SqliteCache, app_db, open_store, set_cache_backend, warm_up
from src.key_loader import load_ors_key

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def transit_status(store=None) -> str:
    """One line on whether the TCAT bus schedule is available, shown when the server starts."""
    store = store or open_store()
    if store is None:
        return "TCAT bus schedule: not built, so the bus card will say so (run: python -m src.update_transit)."
    info = store.feed_info()
    return f"TCAT bus schedule: feed {info['version']}, service {info['start_date']} to {info['end_date']}."


def accounts_status(db_path=None) -> str:
    """One line on the accounts, and what to do when there are none yet."""
    db = app_db.connect(db_path)
    try:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        open_invites = db.execute(
            "SELECT COUNT(*) FROM invites WHERE revoked = 0 AND uses_left > 0 AND (expires_at IS NULL OR expires_at > strftime('%s','now'))"
        ).fetchone()[0]
    finally:
        db.close()
    line = f"Accounts: {users} account{'' if users == 1 else 's'}, {open_invites} open invite code{'' if open_invites == 1 else 's'} ({app_db.DB_PATH})."
    if users == 0 and open_invites == 0:
        line += "\n  Nobody can log in yet. Make a code:  python -m src.manage create-invite --label \"your name\""
    return line


def network_warning(host: str, secure_cookies: bool, behind_proxy: bool) -> str:
    """What to tell the person starting the server when it can be reached from other devices."""
    if host in LOOPBACK:
        return ""
    lines = [f"WARNING: listening on {host}, so other devices can reach it."]
    lines.append("  On a normal network the pages are NOT encrypted: passwords cross it as plain text."
                 if not secure_cookies else "  Cookies are marked secure, so the site must be served over https.")
    if not behind_proxy:
        lines.append("  Prefer a private network (Tailscale) or an https tunnel; see README: Using it from other computers.")
    return "\n".join(lines)


def serve(app, host: str, port: int) -> None:
    """waitress when installed (a real server), else Flask's development server."""
    try:
        from waitress import serve as waitress_serve
    except ImportError:
        print("waitress is not installed, using Flask's development server (pip install -r requirements.txt).")
        app.run(host=host, port=port, threaded=True)
        return
    waitress_serve(app, host=host, port=port, threads=8)


def main(argv=None) -> None:
    import os

    parser = argparse.ArgumentParser(description="Start EcoCommute.")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (default: this computer only)")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)

    source = load_ors_key()
    print(f"OpenRouteService key: found in the {source}." if source else
          "OpenRouteService key: not found, so only sample places and estimates are available "
          "(see README: Run the web entry).")
    print(transit_status())
    print(accounts_status())
    warning = network_warning(args.host, os.environ.get("ECOCOMMUTE_SECURE_COOKIES") == "1",
                              os.environ.get("ECOCOMMUTE_BEHIND_PROXY") == "1")
    if warning:
        print(warning)

    set_cache_backend(SqliteCache(app_db.DB_PATH))  # places searched once are not searched again
    threading.Thread(target=warm_up, daemon=True).start()  # so the first suggestion is not slow
    app = create_app()
    print(f"Open http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}")
    serve(app, args.host, args.port)


if __name__ == "__main__":
    main()
