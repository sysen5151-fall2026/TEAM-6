"""Accounts, invites, limits and per-account trips. Standard library only; every test gets its own database file.

Run:  python -m unittest discover -s tests -t .
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.c2_application_service import accounts
from src.c2_application_service.accounts import AccountError
from src.c3_data_adapter import app_db
from src.c3_data_adapter.trip_store import MemoryTrips, SqliteTrips, other_users_trips
from src.interfaces import ConfirmedTrip

NOW = 1_800_000_000  # a fixed clock, so the limits can be tested without waiting
IP = "10.0.0.7"


def fresh_db():
    folder = Path(tempfile.mkdtemp())
    return app_db.connect(folder / "app.sqlite"), folder / "app.sqlite"


def trip(day="2026-10-27", mode="walk", origin="A", destination="B", km=2.0, co2=0.0, diff=400.0, **kw):
    return ConfirmedTrip(day, mode, origin, destination, km, co2, diff, "walk", **kw)


class TestPasswords(unittest.TestCase):
    def test_the_application_uses_the_real_cost_setting(self):
        self.assertEqual(accounts.SCRYPT, {"n": 2**10, "r": 8, "p": 1})  # the tests' cheap one...
        import importlib

        real = importlib.import_module("src.c2_application_service.accounts").__dict__
        source = Path(real["__file__"]).read_text(encoding="utf-8")
        self.assertIn('SCRYPT = {"n": 2**15, "r": 8, "p": 1}', source)  # ...and the one that ships

    def test_a_hash_is_salted_and_verifies_only_the_right_password(self):
        with mock.patch.object(accounts, "SCRYPT", {"n": 2**15, "r": 8, "p": 1}):
            one, two = accounts.hash_password("correct horse"), accounts.hash_password("correct horse")
        self.assertNotEqual(one, two)  # a new salt each time
        self.assertTrue(accounts.verify_password("correct horse", one))
        for wrong in ("correct horsE", "", "correct horse ", "x" * 500):
            self.assertFalse(accounts.verify_password(wrong, one))
        self.assertTrue(one.startswith("scrypt$15$8$1$"))
        self.assertNotIn("correct", one)

    def test_a_damaged_or_foreign_hash_never_matches_and_never_crashes(self):
        for bad in ("", "plain", "scrypt$15$8$1$zz$zz", "md5$1$2$3$aa$bb", "scrypt$99$8$1$aa$bb", "a$b$c$d$e$f", None):
            with self.subTest(stored=bad):
                self.assertFalse(accounts.verify_password("whatever", bad or ""))

    def test_password_rules(self):
        for bad, why in (("short", "6"), ("x" * 129, "128"), ("Alice.Smith", "same")):
            with self.subTest(password=bad), self.assertRaises(AccountError) as caught:
                accounts.check_password_rules(bad, "alice.smith")
            self.assertIn(why, str(caught.exception))
        for fine in ("a long enough one", "111111", "pass#one"):  # simple ones are the team's own choice
            accounts.check_password_rules(fine, "alice")

    def test_user_names_are_normalised_and_checked(self):
        self.assertEqual(accounts.clean_username("  Alice.Smith "), "alice.smith")
        for bad in ("ab", "", None, "-alice", "al ice", "alice!", "a" * 33, "../etc", "é-user"):
            with self.subTest(name=bad), self.assertRaises(AccountError):
                accounts.clean_username(bad)


class TestInvitesAndSignup(unittest.TestCase):
    def setUp(self):
        self.db, self.path = fresh_db()
        self.addCleanup(self.db.close)

    def register(self, name="alice", password="a good password", code=..., ip=IP, now=NOW):
        if code is ...:  # not given: make a fresh valid one (None and "" are real wrong answers)
            code = accounts.create_invite(self.db, "test", now=now)
        return accounts.register(self.db, name, password, code, ip, now)

    def test_a_valid_invite_makes_an_account_and_is_used_up(self):
        code = accounts.create_invite(self.db, "for alice", now=NOW)
        user = self.register(code=code)
        self.assertEqual(accounts.get_user(self.db, user)["username"], "alice")
        with self.assertRaisesRegex(AccountError, "invite code"):
            self.register("bob", code=code)  # single use

    def test_a_code_can_allow_several_uses_and_the_count_runs_down(self):
        code = accounts.create_invite(self.db, "class", uses=2, now=NOW)
        self.register("one", code=code)
        self.register("two", code=code)
        with self.assertRaises(AccountError):
            self.register("three", code=code)

    def test_codes_are_matched_however_they_are_typed(self):
        code = accounts.create_invite(self.db, now=NOW)
        self.assertTrue(code.startswith("ECO-"))
        typed = code.lower().replace("-", " ")
        self.assertGreater(self.register("alice", code=typed), 0)

    def test_the_code_is_never_stored_in_the_clear(self):
        code = accounts.create_invite(self.db, "secret one", now=NOW)
        stored = " ".join(str(v) for r in self.db.execute("SELECT * FROM invites") for v in tuple(r))
        raw = self.path.read_bytes() + (self.path.with_suffix(".sqlite-wal").read_bytes() if self.path.with_suffix(".sqlite-wal").exists() else b"")
        bare = code.replace("-", "")
        self.assertNotIn(code, stored)
        self.assertNotIn(bare.encode(), raw)

    def test_a_wrong_expired_or_revoked_code_is_refused_without_saying_which(self):
        expired = accounts.create_invite(self.db, "old", days=1, now=NOW)
        revoked = accounts.create_invite(self.db, "gone", now=NOW)
        accounts.revoke_invite(self.db, [i["id"] for i in accounts.list_invites(self.db, NOW) if i["label"] == "gone"][0])
        for code, when in (("ECO-AAAAA-BBBBB", NOW), ("", NOW), (None, NOW), (expired, NOW + 2 * 86400), (revoked, NOW)):
            with self.subTest(code=code):
                with self.assertRaises(AccountError) as caught:
                    self.register("alice", code=code, now=when)
                self.assertEqual(str(caught.exception), "That invite code is not valid, has expired or has been used up.")

    def test_signing_up_counts_as_a_login(self):
        user = self.register()
        self.assertEqual(accounts.get_user(self.db, user)["last_login"], NOW)

    def test_a_taken_name_is_refused_case_insensitively_and_keeps_the_invite(self):
        self.register("Alice")
        code = accounts.create_invite(self.db, now=NOW)
        with self.assertRaisesRegex(AccountError, "taken"):
            self.register("ALICE", code=code)
        self.assertGreater(self.register("alicia", code=code), 0)  # the invite was not spent by the failure

    def test_bad_names_and_passwords_are_refused_before_an_invite_is_used(self):
        code = accounts.create_invite(self.db, now=NOW)
        for name, password in (("a", "a good password"), ("alice", "short")):  # 5 characters
            with self.subTest(name=name), self.assertRaises(AccountError):
                self.register(name, password, code=code)
        self.assertEqual([i["state"] for i in accounts.list_invites(self.db, NOW)], ["open"])

    def test_a_chosen_shared_code_that_never_expires_makes_many_accounts(self):
        accounts.create_invite(self.db, "team", uses=1000, days=0, code="TEAM6-OPEN", now=NOW)
        for i in range(6):  # no daily limit on sign-ups: the site is private
            self.assertGreater(self.register(f"member{i}", code="team6-open", now=NOW + 400 * 86400), 0)

    def test_two_signups_with_one_code_at_once_cannot_both_win(self):
        code = accounts.create_invite(self.db, now=NOW)
        other = app_db.connect(self.path)
        self.addCleanup(other.close)
        accounts.register(self.db, "first", "a good password", code, IP, NOW)
        with self.assertRaises(AccountError):
            accounts.register(other, "second", "a good password", code, "10.2.2.2", NOW)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.db, _ = fresh_db()
        self.addCleanup(self.db.close)
        self.user = accounts.create_user(self.db, "alice", "right password")

    def login(self, name="alice", password="right password", ip=IP, now=NOW):
        return accounts.authenticate(self.db, name, password, ip, now)

    def test_the_right_name_and_password_log_in_whatever_the_case_or_spaces(self):
        self.assertEqual(self.login(), self.user)
        self.assertEqual(self.login(" ALICE "), self.user)

    def test_wrong_name_and_wrong_password_look_the_same(self):
        messages = set()
        for name, password in (("alice", "wrong one here"), ("nobody", "right password"), ("", ""), (None, None)):
            with self.assertRaises(AccountError) as caught:
                self.login(name, password)
            messages.add(str(caught.exception))
        self.assertEqual(messages, {"Wrong user name or password."})

    def test_an_unknown_name_still_costs_a_password_check(self):
        with mock.patch.object(accounts, "_burn_time", wraps=accounts._burn_time) as burn, self.assertRaises(AccountError):
            self.login("nobody")
        burn.assert_called_once()

    def test_five_wrong_tries_lock_that_name_for_a_while(self):
        for _ in range(accounts.LOGIN_FAILS_PER_USER):
            with self.assertRaisesRegex(AccountError, "Wrong"):
                self.login(password="nope nope nope")
        with self.assertRaisesRegex(AccountError, "Too many wrong tries. Wait \\d+ minutes? and try again"):
            self.login()  # even the right password waits
        self.assertEqual(self.login(now=NOW + accounts.LOGIN_WINDOW_S + 5), self.user)

    def test_one_address_trying_many_names_is_locked_too(self):
        for i in range(accounts.LOGIN_FAILS_PER_IP):
            with self.assertRaises(AccountError):
                self.login(f"name{i}", "whatever it is")
        with self.assertRaisesRegex(AccountError, "Too many wrong tries"):
            self.login()
        self.assertEqual(self.login(ip="10.8.8.8"), self.user)  # another address is not affected

    def test_a_good_login_clears_that_names_failures(self):
        for _ in range(3):
            with self.assertRaises(AccountError):
                self.login(password="nope nope nope")
        self.login()
        for _ in range(4):
            with self.assertRaises(AccountError):
                self.login(password="nope nope nope")
        self.assertEqual(self.login(), self.user)  # not locked: the earlier three were forgotten

    def test_the_last_login_time_is_kept(self):
        self.login(now=NOW + 99)
        self.assertEqual(accounts.get_user(self.db, self.user)["last_login"], NOW + 99)


class TestChanges(unittest.TestCase):
    def setUp(self):
        self.db, _ = fresh_db()
        self.addCleanup(self.db.close)
        self.user = accounts.create_user(self.db, "alice", "first password")

    def epoch(self):
        return accounts.get_user(self.db, self.user)["session_epoch"]

    def test_changing_the_password_needs_the_old_one_and_signs_other_sessions_out(self):
        with self.assertRaisesRegex(AccountError, "current password"):
            accounts.change_password(self.db, self.user, "not it", "second password")
        before = self.epoch()
        accounts.change_password(self.db, self.user, "first password", "second password")
        self.assertEqual(self.epoch(), before + 1)
        self.assertEqual(accounts.authenticate(self.db, "alice", "second password", IP, NOW), self.user)
        with self.assertRaises(AccountError):
            accounts.authenticate(self.db, "alice", "first password", IP, NOW)

    def test_the_new_password_must_follow_the_rules(self):
        with self.assertRaises(AccountError):
            accounts.change_password(self.db, self.user, "first password", "short")
        self.assertEqual(self.epoch(), 0)

    def test_a_reset_by_the_manage_tool_signs_everyone_out(self):
        self.assertTrue(accounts.set_password(self.db, "ALICE", "reset password"))
        self.assertEqual(self.epoch(), 1)
        self.assertFalse(accounts.set_password(self.db, "nobody", "reset password"))

    def test_deleting_an_account_removes_its_trips_and_invite_use(self):
        SqliteTrips(self.db, self.user).add(trip())
        self.assertTrue(accounts.delete_user(self.db, self.user))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM trips").fetchone()[0], 0)
        self.assertIsNone(accounts.get_user(self.db, self.user))
        self.assertFalse(accounts.delete_user(self.db, self.user))

    def test_preferences_are_kept_per_account(self):
        other = accounts.create_user(self.db, "bob", "bobs password")
        accounts.set_pref(self.db, self.user, "have", ["bike"])
        self.assertEqual(accounts.get_prefs(self.db, self.user), {"have": ["bike"]})
        self.assertEqual(accounts.get_prefs(self.db, other), {})
        self.db.execute("UPDATE users SET prefs = 'not json' WHERE id = ?", (other,))
        self.assertEqual(accounts.get_prefs(self.db, other), {})  # damaged data is ignored

    def test_names_are_unique_and_create_user_refuses_a_taken_one(self):
        with self.assertRaisesRegex(AccountError, "taken"):
            accounts.create_user(self.db, "Alice", "another password")


class TestDatabase(unittest.TestCase):
    def test_a_fresh_file_has_the_tables_and_foreign_keys_are_enforced(self):
        db, _ = fresh_db()
        self.addCleanup(db.close)
        names = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertTrue({"users", "invites", "trips", "attempts", "place_cache", "suggest_cache", "route_cache"} <= names)
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO trips (user_id, tkey, date, mode, origin, destination, distance_km, co2e_g, difference_g, created_at)"
                       " VALUES (999, 'k', 'd', 'walk', 'a', 'b', 1, 0, 0, 0)")

    def test_a_file_from_another_version_is_not_opened(self):
        db, path = fresh_db()
        db.execute("UPDATE meta SET value = '99' WHERE key = 'schema'")
        db.close()
        with self.assertRaises(app_db.DatabaseError):
            app_db.connect(path)

    def test_a_transaction_is_undone_when_it_fails(self):
        db, _ = fresh_db()
        self.addCleanup(db.close)
        with self.assertRaises(RuntimeError), app_db.transaction(db):
            db.execute("INSERT INTO meta VALUES ('x', 'y')")
            raise RuntimeError("stop")
        self.assertIsNone(db.execute("SELECT 1 FROM meta WHERE key = 'x'").fetchone())

    def test_a_backup_is_a_working_copy(self):
        db, _ = fresh_db()
        self.addCleanup(db.close)
        accounts.create_user(db, "alice", "right password")
        copy = app_db.backup(db, Path(tempfile.mkdtemp()) / "nested" / "copy.sqlite")
        other = app_db.connect(copy)
        self.addCleanup(other.close)
        self.assertEqual(other.execute("SELECT username FROM users").fetchone()[0], "alice")

    def test_data_survives_closing_and_reopening(self):
        db, path = fresh_db()
        user = accounts.create_user(db, "alice", "right password")
        SqliteTrips(db, user).add(trip())
        db.close()
        again = app_db.connect(path)
        self.addCleanup(again.close)
        self.assertEqual(len(SqliteTrips(again, user).all()), 1)
        self.assertEqual(accounts.authenticate(again, "alice", "right password", IP, NOW), user)


class TestTripStores(unittest.TestCase):
    def setUp(self):
        self.db, _ = fresh_db()
        self.addCleanup(self.db.close)
        self.alice = accounts.create_user(self.db, "alice", "alice password")
        self.bob = accounts.create_user(self.db, "bob", "bobs password")

    def stores(self):
        return MemoryTrips(), SqliteTrips(self.db, self.alice)

    def test_both_stores_behave_alike(self):
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                self.assertTrue(store.add(trip()))
                self.assertFalse(store.add(trip()))  # the same trip twice
                self.assertTrue(store.add(trip(destination="C")))
                self.assertEqual([t.destination for t in store.all()], ["B", "C"])
                store.clear()
                self.assertEqual(store.all(), ())

    def test_a_drive_and_a_carpool_of_one_trip_are_one_car_trip_in_both_stores(self):
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                self.assertTrue(store.add(trip(mode="drive", co2=400, diff=0)))
                self.assertFalse(store.add(trip(mode="carpool", co2=133, diff=267, occupants=3)))

    def test_every_field_comes_back_unchanged(self):
        original = trip(mode="bus", route="10", occupants=1, km=2.84, co2=298.0, diff=111.0)
        store = SqliteTrips(self.db, self.alice)
        store.add(original)
        self.assertEqual(store.all(), (original,))
        carpool = trip(mode="carpool", destination="Z", occupants=4)
        store.add(carpool)
        self.assertEqual(store.all()[-1], carpool)

    def test_accounts_do_not_see_each_others_trips(self):
        SqliteTrips(self.db, self.alice).add(trip())
        self.assertEqual(SqliteTrips(self.db, self.bob).all(), ())
        self.assertTrue(SqliteTrips(self.db, self.bob).add(trip()))  # the same trip is allowed for another account
        SqliteTrips(self.db, self.alice).clear()
        self.assertEqual(len(SqliteTrips(self.db, self.bob).all()), 1)  # clearing one leaves the other

    def test_the_others_totals_exclude_you_and_group_by_account(self):
        SqliteTrips(self.db, self.alice).add(trip(destination="A1"))
        SqliteTrips(self.db, self.bob).add(trip(destination="B1"))
        SqliteTrips(self.db, self.bob).add(trip(destination="B2"))
        groups = other_users_trips(self.db, self.alice)
        self.assertEqual([len(g) for g in groups], [2])
        self.assertEqual(sorted(len(g) for g in other_users_trips(self.db, 12345)), [1, 2])  # nobody excluded


if __name__ == "__main__":
    unittest.main()
