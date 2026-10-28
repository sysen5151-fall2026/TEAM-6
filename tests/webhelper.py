"""A web test client that is already signed in and sends the form token by itself.

Every page now needs an account, so the page tests start from `make_client()`. Tests of the log-in
itself use `make_client(login=False)` and `AuthedClient.post(..., csrf=False)`.
"""

import tempfile
from pathlib import Path

from flask.testing import FlaskClient

from src.c1_web_front_end.web_app import create_app
from src.c2_application_service import accounts
from src.c3_data_adapter import SqliteTrips, app_db

TOKEN = "test-form-token"
PASSWORD = "test password"


class AuthedClient(FlaskClient):
    """Adds the form token to every POST unless a test says csrf=False or sends its own."""

    csrf_token = TOKEN

    def open(self, *args, **kwargs):
        csrf = kwargs.pop("csrf", True)
        if csrf and str(kwargs.get("method", "GET")).upper() == "POST":
            data = kwargs.get("data")
            data = {} if data is None else dict(data)
            data.setdefault("csrf_token", self.csrf_token)
            kwargs["data"] = data
        return super().open(*args, **kwargs)


def make_client(username="tester", login=True, db_path=None):
    """A test client for a fresh application with its own database and one account."""
    path = Path(db_path or Path(tempfile.mkdtemp()) / "app.sqlite")
    db = app_db.connect(path)
    try:
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        user_id = existing["id"] if existing else accounts.create_user(db, username, PASSWORD)
    finally:
        db.close()
    app = create_app(db_path=path)
    app.test_client_class = AuthedClient
    client = app.test_client()
    client.user_id, client.db_path, client.username = user_id, path, username
    if login:
        with client.session_transaction() as session:
            session["uid"], session["epoch"], session["csrf"] = user_id, 0, TOKEN
    return client


def store_of(client, test=None):
    """The signed-in account's trip store, to look at or fill directly."""
    db = app_db.connect(client.db_path)
    if test is not None:
        test.addCleanup(db.close)
    return SqliteTrips(db, client.user_id)


def second_account(client, username="visitor"):
    """Another account in the same database; returns its user id."""
    db = app_db.connect(client.db_path)
    try:
        return accounts.create_user(db, username, PASSWORD)
    finally:
        db.close()
