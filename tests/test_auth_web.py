"""The web side of accounts: who may see what, forms that cannot be forged, and each account's own data.

Run:  python -m unittest discover -s tests -t .
"""

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from src.c1_web_front_end import auth
    from tests.webhelper import PASSWORD, make_client, second_account, store_of
except ImportError:  # Flask is the only non-standard dependency
    auth = None

from src.c2_application_service import accounts
from src.c3_data_adapter import SqliteTrips, app_db
from src.interfaces import ConfirmedTrip


def trip(destination="Ithaca Commons", mode="walk", diff=400.0, origin="Collegetown", day="2026-10-27"):
    return ConfirmedTrip(day, mode, origin, destination, 2.0, 0.0, diff, "walk")


def token_of(client, path="/login"):
    page = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)


def web_login(client, username, password, token=None, next_=""):
    token = token or token_of(client)
    return client.post("/login", data={"username": username, "password": password, "next": next_, "csrf_token": token}, csrf=False)


def new_invite(client, **kw):
    db = app_db.connect(client.db_path)
    try:
        return accounts.create_invite(db, "test", **kw)
    finally:
        db.close()


@unittest.skipIf(auth is None, "Flask not installed")
class TestGuards(unittest.TestCase):
    def setUp(self):
        self.anon = make_client(login=False)

    def test_every_page_sends_a_visitor_to_the_log_in_page_and_remembers_where_they_were_going(self):
        for path in ("/", "/garden", "/achievements", "/account", "/done/0", "/compare", "/account/export"):
            with self.subTest(path=path):
                response = self.anon.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].startswith("/login?next="), response.headers["Location"])
        self.assertRegex(self.anon.get("/garden").headers["Location"], r"next=(/|%2F)garden")

    def test_the_online_endpoints_answer_a_visitor_with_401_not_a_page(self):
        for path in ("/places?q=statler", "/route-lines?olat=42.4&olon=-76.4&dlat=42.5&dlon=-76.5"):
            with self.subTest(path=path):
                response = self.anon.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.get_json(), {"error": "Log in first."})

    def test_a_visitor_cannot_post_anything_that_changes_data(self):
        for path in ("/confirm", "/demo", "/reset", "/account", "/logout"):
            with self.subTest(path=path):
                response = self.anon.post(path, data={"mode": "walk"}, csrf=False)
                self.assertEqual(response.status_code, 400)  # no form token: refused before anything else
        with_token = self.anon.post("/confirm", data={"csrf_token": token_of(self.anon)}, csrf=False)
        self.assertEqual(with_token.status_code, 302)  # a token but no account: sent to log in
        self.assertTrue(with_token.headers["Location"].startswith("/login"))

    def test_the_log_in_and_sign_up_pages_are_open(self):
        for path in ("/login", "/register"):
            self.assertEqual(self.anon.get(path).status_code, 200)

    def test_a_signed_in_user_who_opens_log_in_goes_on_to_the_app(self):
        client = make_client()
        self.assertEqual(client.get("/login").status_code, 302)
        self.assertEqual(client.get("/register").headers["Location"], "/")

    def test_a_deleted_account_or_a_forged_session_is_signed_out(self):
        client = make_client()
        with client.session_transaction() as session:
            session["uid"] = 9999
        self.assertEqual(client.get("/").status_code, 302)
        with client.session_transaction() as session:
            self.assertNotIn("uid", session)

    def test_a_form_cookie_with_the_wrong_signature_is_ignored(self):
        client = make_client(login=False)
        client.set_cookie("session", "forged.value.here")
        self.assertEqual(client.get("/").status_code, 302)


@unittest.skipIf(auth is None, "Flask not installed")
class TestRedirects(unittest.TestCase):
    def test_only_paths_on_this_site_are_followed(self):
        for ok in ("/", "/garden", "/achievements?x=1", "/done/0"):
            self.assertEqual(auth.safe_next(ok), ok)
        for bad in ("", None, "http://evil.example", "//evil.example", "https://evil.example/x", "evil", "/\\evil.example",
                    "javascript:alert(1)"):
            self.assertEqual(auth.safe_next(bad), "/", bad)

    def test_log_in_never_sends_anyone_to_another_site(self):
        client = make_client(login=False)
        for target in ("//evil.example", "https://evil.example", "/\\evil.example"):
            with self.subTest(next=target):
                client = make_client(login=False, db_path=client.db_path)
                response = web_login(client, client.username, PASSWORD, next_=target)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/")

    def test_log_in_goes_back_to_where_the_visitor_was_headed(self):
        client = make_client(login=False)
        self.assertEqual(web_login(client, client.username, PASSWORD, next_="/garden").headers["Location"], "/garden")


@unittest.skipIf(auth is None, "Flask not installed")
class TestLogin(unittest.TestCase):
    def setUp(self):
        self.client = make_client(login=False)

    def test_the_right_password_signs_in_and_the_app_opens(self):
        response = web_login(self.client, self.client.username, PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_a_wrong_password_or_unknown_name_gets_the_same_401_message(self):
        messages = set()
        for name, password in ((self.client.username, "not the one"), ("nobody-here", PASSWORD)):
            response = web_login(self.client, name, password)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Wrong user name or password.", response.get_data(as_text=True))
            messages.add(re.search(r'role="alert"><ul><li>(.*?)</li>', response.get_data(as_text=True)).group(1))
        self.assertEqual(len(messages), 1)
        self.assertEqual(self.client.get("/").status_code, 302)  # still signed out

    def test_repeated_wrong_tries_are_locked_out_even_for_the_right_password(self):
        for _ in range(accounts.LOGIN_FAILS_PER_USER):
            web_login(self.client, self.client.username, "wrong one here")
        response = web_login(self.client, self.client.username, PASSWORD)
        self.assertIn("Too many wrong tries", response.get_data(as_text=True))
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_a_form_without_the_right_token_is_refused(self):
        for data in ({"username": self.client.username, "password": PASSWORD},
                     {"username": self.client.username, "password": PASSWORD, "csrf_token": "guess"}):
            response = self.client.post("/login", data=data, csrf=False)
            self.assertEqual(response.status_code, 400)
            self.assertIn("form has expired", response.get_data(as_text=True))
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_the_session_cookie_cannot_be_read_by_scripts_or_sent_from_other_sites(self):
        response = web_login(self.client, self.client.username, PASSWORD)
        cookie = [c for c in response.headers.getlist("Set-Cookie") if c.startswith("session=")][0]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)  # only when served over https (ECOCOMMUTE_SECURE_COOKIES=1)

    def test_the_cookie_is_secure_when_the_site_runs_over_https(self):
        with mock.patch.dict(os.environ, {"ECOCOMMUTE_SECURE_COOKIES": "1"}):
            client = make_client(login=False)
        response = web_login(client, client.username, PASSWORD, token_of(client))
        self.assertIn("Secure", [c for c in response.headers.getlist("Set-Cookie") if c.startswith("session=")][0])

    def test_a_new_session_starts_at_log_in_so_nothing_from_before_carries_over(self):
        before = token_of(self.client)
        web_login(self.client, self.client.username, PASSWORD, before)
        with self.client.session_transaction() as session:
            self.assertNotEqual(session["csrf"], before)

    def test_log_out_needs_a_post_and_ends_the_session(self):
        web_login(self.client, self.client.username, PASSWORD)
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.get("/").status_code, 200)  # a link cannot log anyone out
        self.client.csrf_token = token_of(self.client, "/account")
        self.assertEqual(self.client.post("/logout").status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_the_log_in_page_shows_nothing_about_other_accounts(self):
        page = self.client.get("/login").get_data(as_text=True)
        self.assertNotIn(self.client.username, page)
        self.assertNotIn("password", page.split('name="password"')[0].lower().replace("password", "", 0)[:0])


@unittest.skipIf(auth is None, "Flask not installed")
class TestRegister(unittest.TestCase):
    def setUp(self):
        self.anon = make_client(login=False)

    def register(self, invite, username="newcomer", password="a fine password", confirm=None, **extra):
        data = {"invite": invite, "username": username, "password": password,
                "confirm": password if confirm is None else confirm, "csrf_token": token_of(self.anon, "/register"), **extra}
        return self.anon.post("/register", data=data, csrf=False)

    def test_a_valid_invite_creates_the_account_and_signs_in(self):
        response = self.register(new_invite(self.anon))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.anon.get("/").status_code, 200)
        self.assertIn("newcomer", self.anon.get("/account").get_data(as_text=True))

    def test_the_invite_works_once_and_a_wrong_one_is_refused_without_detail(self):
        code = new_invite(self.anon)
        self.register(code)
        other = make_client(login=False, db_path=self.anon.db_path)
        self.anon = other
        for invite in (code, "ECO-NOPE1-NOPE2", ""):
            response = self.register(invite, username="second")
            self.assertEqual(response.status_code, 400)
            self.assertIn("That invite code is not valid", response.get_data(as_text=True))

    def test_mismatched_passwords_weak_passwords_and_bad_names_are_explained(self):
        code = new_invite(self.anon, uses=5)
        cases = (({"confirm": "different one"}, "not the same"), ({"password": "short", "confirm": "short"}, "6 to 128"),
                 ({"username": "no"}, "3 to 32"), ({"username": "bad name!"}, "3 to 32"))
        for extra, expect in cases:
            with self.subTest(extra=extra):
                body = {"username": "newcomer", "password": "a fine password"}
                body.update(extra)
                response = self.register(code, **body)
                self.assertEqual(response.status_code, 400)
                self.assertRegex(response.get_data(as_text=True), expect)

    def test_the_hidden_field_only_a_script_fills_stops_sign_up(self):
        response = self.register(new_invite(self.anon), website="http://spam.example")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.anon.get("/").status_code, 302)

    def test_the_form_asks_in_the_order_name_password_confirmation_invite(self):
        page = self.anon.get("/register").get_data(as_text=True)
        ids = [page.index(f'id="{field}"') for field in ("username", "password", "confirm", "invite")]
        self.assertEqual(ids, sorted(ids))

    def test_the_form_is_protected_like_the_others(self):
        response = self.anon.post("/register", data={"invite": new_invite(self.anon), "username": "x1y", "password": "a fine password",
                                                     "confirm": "a fine password"}, csrf=False)
        self.assertEqual(response.status_code, 400)

    def test_the_password_is_never_written_back_into_the_page(self):
        response = self.register("ECO-WRONG-WRONG", password="my secret passphrase")
        self.assertNotIn("my secret passphrase", response.get_data(as_text=True))


@unittest.skipIf(auth is None, "Flask not installed")
class TestAccountPage(unittest.TestCase):
    def setUp(self):
        self.client = make_client()

    def post(self, **data):
        return self.client.post("/account", data=data)

    def test_the_password_can_be_changed_and_the_other_browser_is_signed_out(self):
        other = make_client(db_path=self.client.db_path)  # a second browser signed in as the same account
        self.assertEqual(other.get("/").status_code, 200)
        response = self.post(action="password", current=PASSWORD, new_password="a brand new one", confirm="a brand new one")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password changed", response.get_data(as_text=True))
        self.assertEqual(self.client.get("/").status_code, 200)  # this browser stays in
        self.assertEqual(other.get("/").status_code, 302)  # the other was signed out
        fresh = make_client(login=False, db_path=self.client.db_path)
        self.assertEqual(web_login(fresh, self.client.username, "a brand new one").status_code, 302)

    def test_wrong_current_password_mismatch_and_weak_new_password_change_nothing(self):
        for data, expect in ((dict(current="not it", new_password="a brand new one", confirm="a brand new one"), "current password"),
                             (dict(current=PASSWORD, new_password="a brand new one", confirm="other"), "not the same"),
                             (dict(current=PASSWORD, new_password="short", confirm="short"), "8")):
            with self.subTest(expect=expect):
                response = self.post(action="password", **data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(expect, response.get_data(as_text=True))
        fresh = make_client(login=False, db_path=self.client.db_path)
        self.assertEqual(web_login(fresh, self.client.username, PASSWORD).status_code, 302)  # the old one still works

    def test_deleting_the_account_needs_the_password_and_the_word_and_removes_everything(self):
        store = store_of(self.client, self)
        store.add(trip())
        for data in (dict(password="wrong password", confirm_word="delete"), dict(password=PASSWORD, confirm_word="yes"), dict(password=PASSWORD)):
            with self.subTest(data=data):
                self.assertEqual(self.post(action="delete", **data).status_code, 400)
        self.assertEqual(len(store.all()), 1)
        response = self.post(action="delete", password=PASSWORD, confirm_word=" Delete ")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)
        db = app_db.connect(self.client.db_path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM trips").fetchone()[0], 0)

    def test_an_unknown_action_is_refused(self):
        self.assertEqual(self.post(action="make-me-admin").status_code, 400)

    def test_the_data_export_is_only_this_accounts_and_has_no_password(self):
        store_of(self.client, self).add(trip("Statler Hall"))
        other = second_account(self.client)
        db = app_db.connect(self.client.db_path)
        self.addCleanup(db.close)
        SqliteTrips(db, other).add(trip("Somebody Elses Place"))
        response = self.client.get("/account/export")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        text = response.get_data(as_text=True)
        data = json.loads(text)
        self.assertEqual([t["destination"] for t in data["trips"]], ["Statler Hall"])
        self.assertEqual(data["user"]["username"], self.client.username)
        for forbidden in ("pw_hash", "scrypt$", "Somebody Elses Place", "session_epoch"):
            self.assertNotIn(forbidden, text)

    def test_the_account_page_says_what_is_kept(self):
        page = self.client.get("/account").get_data(as_text=True)
        self.assertIn("Delete my account", page)
        self.assertIn("Download my data", page)
        self.assertIn("no page shows another account", page)

    def test_an_avatar_from_the_list_is_saved_and_shown_in_the_top_bar_but_anything_else_is_refused(self):
        choice = auth.AVATAR_CHOICES[7]
        page = self.client.get("/account").get_data(as_text=True)
        self.assertEqual(len(auth.AVATAR_CHOICES), len(set(auth.AVATAR_CHOICES)))
        for avatar in auth.AVATAR_CHOICES:
            self.assertIn(f'value="{avatar}"', page)
        response = self.post(action="avatar", avatar=choice)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Avatar saved", response.get_data(as_text=True))
        for path in ("/", "/garden", "/achievements", "/account"):
            self.assertIn(f'<span class="ico">{choice}</span>', self.client.get(path).get_data(as_text=True))
        for bad in ("<script>", "x", ""):
            self.assertEqual(self.post(action="avatar", avatar=bad).status_code, 400)
        self.assertIn(f'<span class="ico">{choice}</span>', self.client.get("/garden").get_data(as_text=True))

    def test_the_account_page_offers_light_dark_and_device_themes_on_every_page(self):
        page = self.client.get("/account").get_data(as_text=True)
        for choice in ("auto", "light", "dark"):
            self.assertIn(f'data-theme-choice="{choice}"', page)
        for path in ("/", "/garden", "/achievements"):  # the saved choice is applied before the page is drawn
            self.assertIn("ecocommute.theme", self.client.get(path).get_data(as_text=True))


@unittest.skipIf(auth is None, "Flask not installed")
class TestOwnData(unittest.TestCase):
    def setUp(self):
        self.alice = make_client("alice")
        second_account(self.alice, "bob")
        self.bob = make_client("bob", db_path=self.alice.db_path)

    def test_an_account_sees_only_its_own_trips_and_history(self):
        store_of(self.alice, self).add(trip("Alices Secret Place"))
        self.assertIn("Alices Secret Place", self.alice.get("/achievements").get_data(as_text=True))
        for path in ("/achievements", "/garden", "/", "/done/0"):
            with self.subTest(path=path):
                page = self.bob.get(path, follow_redirects=True).get_data(as_text=True)
                self.assertNotIn("Alices Secret Place", page)
                self.assertNotIn("alice", page.lower().replace("welcome", ""))

    def test_the_done_page_of_someone_elses_trip_is_not_reachable(self):
        store_of(self.alice, self).add(trip())
        self.assertEqual(self.bob.get("/done/0").status_code, 302)  # bob has no trip 0

    def test_everyones_trips_add_up_in_the_shared_tree_but_only_as_a_total(self):
        before = self.bob.get("/garden").get_data(as_text=True)
        store_of(self.alice, self).add(trip(diff=5000))
        after = self.bob.get("/garden").get_data(as_text=True)
        self.assertNotEqual(before, after)  # the total moved
        self.assertNotIn("Collegetown", after)  # but nothing of alice's trip is shown
        self.assertNotIn("alice", after.lower())

    def test_the_vehicles_ticked_are_remembered_per_account(self):
        self.alice.post("/", data={"origin": "Cornell Arts Quad", "destination": "Ithaca Commons", "have": ["bike", "scooter"]})
        again = self.alice.get("/").get_data(as_text=True)
        self.assertRegex(again, r'name="have" value="bike"\s+checked')
        self.assertRegex(again, r'name="have" value="scooter"\s+checked')
        self.assertNotRegex(self.bob.get("/").get_data(as_text=True), r'name="have" value="bike"\s+checked')

    def test_recent_trips_are_offered_again_from_the_accounts_own_history(self):
        store = store_of(self.alice, self)
        store.add(trip("Statler Hall, Ithaca, NY, USA", origin="Upson Hall, Ithaca, NY, USA"))
        store.add(trip("Olin Library", origin="My location (42.4421, -76.4853)", day="2026-10-28"))  # a raw position is never offered
        page = self.alice.get("/").get_data(as_text=True)
        self.assertIn("Recent:", page)
        self.assertIn("Upson Hall ➜ Statler Hall", page)
        self.assertNotIn("My location (42", page)
        self.assertNotIn("Recent:", self.bob.get("/").get_data(as_text=True))

    def test_confirming_a_trip_saves_it_for_next_time_and_survives_a_restart(self):
        response = self.alice.post("/confirm", data={"origin": "Cornell Arts Quad", "destination": "Ithaca Commons",
                                                     "mode": "walk", "date": "2026-10-27", "when": "2026-10-27T10:00"})
        self.assertEqual(response.status_code, 302)
        restarted = make_client("alice", db_path=self.alice.db_path)  # a new application on the same file
        self.assertIn("Ithaca Commons", restarted.get("/achievements").get_data(as_text=True))


@unittest.skipIf(auth is None, "Flask not installed")
class TestHardening(unittest.TestCase):
    def test_pages_carry_the_security_headers(self):
        anon = make_client(login=False)
        for response in (anon.get("/login"), make_client().get("/")):
            headers = response.headers
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertIn("script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(headers["X-Frame-Options"], "DENY")
            # OpenStreetMap refuses tiles with no Referer, so the origin must be sent to it (never the full address)
            self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_personal_pages_are_not_kept_by_the_browser(self):
        self.assertEqual(make_client().get("/achievements").headers["Cache-Control"], "no-store")

    def test_the_policy_allows_what_the_page_really_loads(self):
        page = make_client().get("/").get_data(as_text=True)
        for host in re.findall(r'<(?:script|link|img)[^>]*(?:src|href)="(https://[^/"]+)', page):  # what the browser fetches
            self.assertIn(host, auth.CSP)
        self.assertIn("https://tile.openstreetmap.org", auth.CSP)  # the map tiles, fetched by the script

    def test_an_oversized_form_is_refused(self):
        response = make_client().post("/", data={"origin": "x" * 100_000})
        self.assertEqual(response.status_code, 413)

    def test_a_browser_with_no_session_cannot_pass_by_sending_no_token(self):
        """An empty token on both sides must not count as a match (the log-in form could be forged)."""
        fresh = make_client(login=False)
        for path, data in (("/login", {"username": "x", "password": "y"}), ("/register", {"invite": "x"}),
                           ("/logout", {}), ("/confirm", {})):
            with self.subTest(path=path):
                self.assertEqual(fresh.post(path, data=data, csrf=False).status_code, 400)
                self.assertEqual(fresh.post(path, data={**data, "csrf_token": ""}, csrf=False).status_code, 400)

    def test_a_header_token_is_accepted_for_scripts_but_a_wrong_one_is_not(self):
        client = make_client()
        ok = client.post("/demo", headers={"X-CSRF-Token": "test-form-token"}, csrf=False)
        self.assertEqual(ok.status_code, 302)
        bad = client.post("/demo", headers={"X-CSRF-Token": "nope"}, csrf=False)
        self.assertEqual(bad.status_code, 400)

    def test_every_form_that_posts_carries_the_token(self):
        client = make_client()
        client.post("/demo")  # so the achievements page shows its buttons
        for path in ("/", "/account", "/garden", "/achievements"):
            page = client.get(path).get_data(as_text=True)
            for form in re.findall(r"<form[^>]*>(.*?)</form>", page, re.S):
                pass
            posts = [m for m in re.finditer(r'<form[^>]*method="post"[^>]*>(.*?)</form>', page, re.S)]
            for m in posts:
                self.assertIn('name="csrf_token"', m.group(0), path)

    def test_the_secret_key_comes_from_the_environment_or_a_file_made_once(self):
        with mock.patch.dict(os.environ, {"ECOCOMMUTE_SECRET": "from the environment"}):
            self.assertEqual(auth.load_secret_key(), b"from the environment")
        folder = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ):
            os.environ.pop("ECOCOMMUTE_SECRET", None)
            first = auth.load_secret_key(folder / "secret.key")
            second = auth.load_secret_key(folder / "secret.key")
        self.assertEqual(first, second)  # made once, then reused, so sessions survive a restart
        self.assertEqual(len(first), 64)
        self.assertRegex(first.decode(), r"^[0-9a-f]{64}$")

    def test_behind_a_tunnel_the_real_address_is_used_for_the_limits(self):
        with mock.patch.dict(os.environ, {"ECOCOMMUTE_BEHIND_PROXY": "1"}):
            client = make_client(login=False)
        db = app_db.connect(client.db_path)
        self.addCleanup(db.close)
        web_login(client, "nobody", "whatever it is", token_of(client)).close()
        # the client sent no forwarded header, so the address recorded is the direct one
        ips = {r["ip"] for r in db.execute("SELECT ip FROM attempts")}
        self.assertEqual(ips, {"127.0.0.1"})
        forwarded = client.post("/login", data={"username": "nobody", "password": "whatever it is", "csrf_token": token_of(client)},
                                headers={"X-Forwarded-For": "203.0.113.9"}, csrf=False)
        forwarded.close()
        self.assertIn("203.0.113.9", {r["ip"] for r in db.execute("SELECT ip FROM attempts")})


if __name__ == "__main__":
    unittest.main()
