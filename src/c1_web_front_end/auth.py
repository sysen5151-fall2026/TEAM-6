"""Log-in, sessions, forgery protection and the page guards for the web pages (C.1).

Every page except the log-in and sign-up pages needs a signed-in account, and so do the two
JSON endpoints that spend the online-service quota. The session is a signed cookie holding the
account id and a counter that is raised when the password changes, so changing it signs every
other browser out. Every form that changes something carries a secret token (CSRF).
"""

import hmac
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Response, abort, g, jsonify, redirect, render_template, request, session, url_for
from markupsafe import Markup

from src.c2_application_service import accounts
from src.c2_application_service.accounts import AccountError
from src.c3_data_adapter import SqliteTrips, app_db, other_users_trips

PUBLIC_ENDPOINTS = {"login_page", "register_page", "static"}
JSON_ENDPOINTS = {"places_api", "route_lines_api"}
SESSION_DAYS = 14

TONES = ("", "\U0001F3FB", "\U0001F3FC", "\U0001F3FD", "\U0001F3FE", "\U0001F3FF")
HAIR = {"red": "\u200d\U0001F9B0", "curly": "\u200d\U0001F9B1", "white": "\u200d\U0001F9B3", "bald": "\u200d\U0001F9B2",
        "blond_f": "\u200d\u2640\ufe0f", "blond_m": "\u200d\u2642\ufe0f", "": ""}


def _person(head: str, tone: int, hair: str = "") -> str:
    return head + TONES[tone] + HAIR[hair]


GIRL, BOY, CHILD, WOMAN, MAN, PERSON = "\U0001F467", "\U0001F466", "\U0001F9D2", "\U0001F469", "\U0001F468", "\U0001F9D1"
OLD_WOMAN, OLD_MAN, OLD_PERSON, BLOND = "\U0001F475", "\U0001F474", "\U0001F9D3", "\U0001F471"
BEARD, HEADSCARF, TURBAN = "\U0001F9D4", "\U0001F9D5", "\U0001F473"
AVATAR_CHOICES = tuple(_person(*spec) for spec in (  # ready-made faces: kids, grown-ups and older people, many skin tones and hair styles
    (GIRL, 1), (GIRL, 4), (BOY, 3), (BOY, 5), (CHILD, 2), (CHILD, 0),
    (WOMAN, 3), (WOMAN, 5), (MAN, 1), (MAN, 4), (PERSON, 2), (PERSON, 0),
    (WOMAN, 1, "red"), (MAN, 3, "red"), (WOMAN, 5, "curly"), (MAN, 4, "curly"),
    (BLOND, 1, "blond_f"), (BLOND, 2, "blond_m"), (WOMAN, 3, "white"), (MAN, 5, "white"),
    (WOMAN, 4, "bald"), (MAN, 2, "bald"), (BEARD, 3), (HEADSCARF, 2), (TURBAN, 4),
    (OLD_WOMAN, 1), (OLD_MAN, 4), (OLD_PERSON, 5), (OLD_WOMAN, 3), (OLD_MAN, 2),
))
DEFAULT_AVATAR = "\U0001F464"
AVATARS = {DEFAULT_AVATAR, *AVATAR_CHOICES}


def avatar_of(user) -> str:
    try:
        choice = json.loads(user["prefs"] or "{}").get("avatar", "")
    except (ValueError, AttributeError, TypeError):
        return DEFAULT_AVATAR
    return choice if choice in AVATARS else DEFAULT_AVATAR

CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https://tile.openstreetmap.org https://cdnjs.cloudflare.com; "
    "connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def load_secret_key(path=None) -> bytes:
    """The key that signs session cookies: from ECOCOMMUTE_SECRET, else a file made on first use."""
    env = os.environ.get("ECOCOMMUTE_SECRET", "").strip()
    if env:
        return env.encode()
    path = Path(path or app_db.DB_PATH.parent / "secret.key")
    if path.exists():
        return path.read_text(encoding="utf-8").strip().encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key.encode()


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def csrf_input() -> Markup:
    return Markup(f'<input type="hidden" name="csrf_token" value="{csrf_token()}">')


def safe_next(target: str) -> str:
    """Only paths on this site: a log-in link must never send anyone elsewhere."""
    target = target or ""
    return target if target.startswith("/") and not target.startswith("//") and "\\" not in target else "/"


def client_ip() -> str:
    return request.remote_addr or ""


def current_trips():
    return g.trips


def community_trips() -> tuple:
    return other_users_trips(g.db, g.user["id"])


def init_auth(app, db_path=None):
    """Wire accounts into the app: configuration, guards, headers and the account pages."""
    app.config.update(
        DB_PATH=str(db_path or app_db.DB_PATH),
        SECRET_KEY=load_secret_key(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("ECOCOMMUTE_SECURE_COOKIES") == "1",  # set it when served over https
        PERMANENT_SESSION_LIFETIME=timedelta(days=SESSION_DAYS),
        MAX_CONTENT_LENGTH=64 * 1024,  # no form here is anywhere near this
    )
    if os.environ.get("ECOCOMMUTE_BEHIND_PROXY") == "1":  # a tunnel in front: trust its address and scheme headers
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.jinja_env.globals["csrf_input"] = csrf_input

    @app.before_request
    def guard():
        g.db = app_db.connect(app.config["DB_PATH"])
        g.user = None
        row = accounts.get_user(g.db, session.get("uid")) if session.get("uid") else None
        if row is not None and session.get("epoch") == row["session_epoch"]:
            g.user = row
            g.trips = SqliteTrips(g.db, row["id"])
        elif session.get("uid"):
            session.clear()  # the account is gone or its password changed

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            expected = session.get("csrf", "")
            # An empty expected token (a browser with no session yet) must never match an empty one sent.
            if not expected or not hmac.compare_digest(sent.encode(), expected.encode()):
                return render_template("message.html", active="", title="That form has expired",
                                       text="Go back, reload the page and try again."), 400
        if g.user is None and request.endpoint not in PUBLIC_ENDPOINTS:
            if request.endpoint in JSON_ENDPOINTS:
                return jsonify({"error": "Log in first."}), 401
            return redirect(url_for("login_page", next=request.full_path.rstrip("?")))
        return None

    @app.teardown_request
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def who():
        user = g.get("user")
        return {"current_user": user, "current_user_avatar": avatar_of(user) if user else DEFAULT_AVATAR}

    @app.after_request
    def headers(response: Response):
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")  # map tiles are refused without a Referer
        if g.get("user") is not None:
            response.headers["Cache-Control"] = "no-store"  # personal pages are not kept by the browser
        return response

    # ------------------------------------------------------------------ pages
    def start_session(user_id: int) -> None:
        row = accounts.get_user(g.db, user_id)
        session.clear()  # a new session, so nothing from before log-in carries over
        session.permanent = True
        session["uid"], session["epoch"] = row["id"], row["session_epoch"]
        csrf_token()

    def login_page():
        if g.user is not None:
            return redirect(safe_next(request.args.get("next", "")))
        error = ""
        if request.method == "POST":
            try:
                user_id = accounts.authenticate(g.db, request.form.get("username", ""),
                                                request.form.get("password", ""), client_ip())
            except AccountError as err:
                error = str(err)
            else:
                start_session(user_id)
                return redirect(safe_next(request.form.get("next", "")))
        return render_template("login.html", active="", error=error, next=safe_next(request.values.get("next", "")),
                               username=request.form.get("username", "")[:40]), (401 if error else 200)

    def register_page():
        if g.user is not None:
            return redirect("/")
        error = ""
        form = request.form
        if request.method == "POST":
            try:
                if form.get("password", "") != form.get("confirm", ""):
                    raise AccountError("The two passwords are not the same.")
                if form.get("website", ""):  # a field people never see: only a script fills it
                    raise AccountError("That invite code is not valid, has expired or has been used up.")
                user_id = accounts.register(g.db, form.get("username", ""), form.get("password", ""),
                                            form.get("invite", ""), client_ip())
            except AccountError as err:
                error = str(err)
            else:
                start_session(user_id)
                return redirect("/")
        return render_template("register.html", active="", error=error, username=form.get("username", "")[:40],
                               invite=form.get("invite", "")[:40]), (400 if error else 200)

    def logout_page():
        session.clear()
        return redirect(url_for("login_page"))

    def account_page():
        message = error = ""
        if request.method == "POST":
            action = request.form.get("action", "")
            try:
                if action == "password":
                    if request.form.get("new_password", "") != request.form.get("confirm", ""):
                        raise AccountError("The two new passwords are not the same.")
                    accounts.change_password(g.db, g.user["id"], request.form.get("current", ""),
                                             request.form.get("new_password", ""))
                    start_session(g.user["id"])  # this browser stays signed in; the others are signed out
                    message = "Password changed. Other browsers were signed out."
                elif action == "delete":
                    if request.form.get("confirm_word", "").strip().lower() != "delete":
                        raise AccountError('Type the word "delete" to confirm.')
                    if not accounts.verify_password(request.form.get("password", ""), g.user["pw_hash"]):
                        raise AccountError("The password is not right.")
                    accounts.delete_user(g.db, g.user["id"])
                    session.clear()
                    return redirect(url_for("login_page"))
                elif action == "avatar":
                    choice = request.form.get("avatar", "")
                    if choice not in AVATARS:
                        raise AccountError("Pick one of the avatars on the list.")
                    accounts.set_pref(g.db, g.user["id"], "avatar", choice)
                    g.user = accounts.get_user(g.db, g.user["id"])  # the top bar shows the new one at once
                    message = "Avatar saved."
                else:
                    abort(400)
            except AccountError as err:
                error = str(err)
        user = accounts.get_user(g.db, g.user["id"])
        return render_template("account.html", active="account", message=message, error=error, user=user,
                               avatar=avatar_of(user), avatar_choices=AVATAR_CHOICES,
                               trip_count=len(g.trips.all())), (400 if error else 200)

    def export_page():
        user = accounts.get_user(g.db, g.user["id"])
        data = {
            "user": {"username": user["username"], "created_at": user["created_at"]},
            "preferences": accounts.get_prefs(g.db, user["id"]),
            "trips": [t.__dict__ for t in g.trips.all()],
        }
        return Response(json.dumps(data, indent=2), mimetype="application/json",
                        headers={"Content-Disposition": "attachment; filename=ecocommute-my-data.json"})

    app.add_url_rule("/login", view_func=login_page, endpoint="login_page", methods=["GET", "POST"])
    app.add_url_rule("/register", view_func=register_page, endpoint="register_page", methods=["GET", "POST"])
    app.add_url_rule("/logout", view_func=logout_page, endpoint="logout_page", methods=["POST"])
    app.add_url_rule("/account", view_func=account_page, endpoint="account_page", methods=["GET", "POST"])
    app.add_url_rule("/account/export", view_func=export_page, endpoint="export_page")
