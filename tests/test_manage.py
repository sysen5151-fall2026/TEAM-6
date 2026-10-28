"""The manage tool: invites, accounts, backups. Nothing here needs Flask.

Run:  python -m unittest discover -s tests -t .
"""

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import manage
from src.c2_application_service import accounts
from src.c3_data_adapter import SqliteTrips, app_db


class Base(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "app.sqlite"
        self.lines = []

    def run_tool(self, *argv, passwords=(), answers=()):
        self.lines.clear()
        with mock.patch("getpass.getpass", side_effect=list(passwords)), mock.patch("builtins.input", side_effect=list(answers)):
            code = manage.main(["--db", str(self.path), *argv], out=self.lines.append)
        return code

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def db(self):
        db = app_db.connect(self.path)
        self.addCleanup(db.close)
        return db


class TestSeed(Base):
    ROSTER = {"invites": [{"label": "team", "code": "TEAM6-ONE"}, {"label": "prof", "code": "TEAM6-TWO"}],
              "users": [{"username": "karen", "password": "pass#one"},
                        {"username": "test01", "password": "111111", "demo": True, "sample_trips": True}]}

    def seed(self, roster=None):
        file = self.path.with_name("roster.json")
        file.write_text(__import__("json").dumps(roster or self.ROSTER), encoding="utf-8")
        return self.run_tool("seed", "--file", str(file))

    def test_named_accounts_and_chosen_codes_are_created_and_work(self):
        self.assertEqual(self.seed(), 0)
        db = self.db()
        self.assertGreater(accounts.authenticate(db, "karen", "pass#one", "10.0.0.1"), 0)
        self.assertGreater(accounts.authenticate(db, "test01", "111111", "10.0.0.1"), 0)
        self.assertGreater(accounts.register(db, "newperson", "a password", "team6-one", "10.0.0.1"), 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM trips WHERE user_id = 2").fetchone()[0] > 0, True)  # sample trips
        self.assertNotIn("pass#one", self.text)  # passwords are never echoed

    def test_running_it_again_changes_nothing(self):
        self.seed()
        self.seed()
        self.assertIn("already exists", self.text)
        db = self.db()
        self.assertEqual(db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 2)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM invites").fetchone()[0], 2)

    def test_a_missing_file_says_so(self):
        self.assertEqual(self.run_tool("seed", "--file", str(self.path.with_name("none.json"))), 1)
        self.assertIn("No roster file", self.text)


class TestInvites(Base):
    def test_a_code_is_printed_once_and_works_for_sign_up(self):
        self.assertEqual(self.run_tool("create-invite", "--label", "Karen"), 0)
        code = re.search(r"ECO-[A-Z0-9]{5}-[A-Z0-9]{5}", self.text).group(0)
        self.assertIn("only time", self.text)
        user = accounts.register(self.db(), "karen", "karens password", code, "10.0.0.1")
        self.assertGreater(user, 0)

    def test_the_list_never_shows_a_code_and_shows_each_state(self):
        self.run_tool("create-invite", "--label", "one")
        code = re.search(r"ECO-[A-Z0-9]{5}-[A-Z0-9]{5}", self.text).group(0)
        self.run_tool("create-invite", "--label", "two")
        self.run_tool("revoke-invite", "2")
        self.assertEqual(self.run_tool("invites"), 0)
        self.assertNotIn(code, self.text)
        self.assertNotIn(code.replace("-", ""), self.text)
        self.assertRegex(self.text, r"#1\s+open")
        self.assertRegex(self.text, r"#2\s+revoked")

    def test_options_set_uses_and_days(self):
        self.run_tool("create-invite", "--uses", "3", "--days", "2")
        self.assertIn("uses: 3", self.text)
        self.assertIn("valid for 2 days", self.text)
        self.assertEqual(accounts.list_invites(self.db())[0]["uses_left"], 3)

    def test_revoking_an_unknown_invite_says_so_and_fails(self):
        self.assertEqual(self.run_tool("revoke-invite", "99"), 1)
        self.assertIn("No such invite", self.text)

    def test_an_empty_list_says_how_to_start(self):
        self.run_tool("invites")
        self.assertIn("create-invite", self.text)


class TestUsers(Base):
    def test_a_generated_password_is_shown_once_and_logs_in(self):
        self.assertEqual(self.run_tool("create-user", "Prof", "--generate"), 0)
        password = re.search(r"Password \(shown once\): (\S+)", self.text).group(1)
        self.assertEqual(len(password), 16)
        self.assertEqual(accounts.authenticate(self.db(), "prof", password, "10.0.0.1"), 1)

    def test_a_typed_password_is_asked_twice_and_never_printed(self):
        self.assertEqual(self.run_tool("create-user", "tutor", passwords=["a typed password", "a typed password"]), 0)
        self.assertNotIn("a typed password", self.text)
        self.assertEqual(accounts.authenticate(self.db(), "tutor", "a typed password", "10.0.0.1"), 1)

    def test_two_different_passwords_make_no_account(self):
        self.assertEqual(self.run_tool("create-user", "ta", passwords=["one password here", "another one here"]), 1)
        self.assertIn("not the same", self.text)
        self.assertEqual(self.db().execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)

    def test_bad_names_taken_names_and_weak_passwords_are_refused_with_a_message(self):
        self.assertEqual(self.run_tool("create-user", "x", "--generate"), 1)
        self.run_tool("create-user", "alice", "--generate")
        self.assertEqual(self.run_tool("create-user", "ALICE", "--generate"), 1)
        self.assertIn("taken", self.text)
        self.assertEqual(self.run_tool("create-user", "bob", passwords=["short", "short"]), 1)

    def test_a_demo_account_can_start_with_labelled_sample_trips(self):
        self.assertEqual(self.run_tool("create-user", "demo1", "--generate", "--with-sample-trips"), 0)
        self.assertIn("sample trips", self.text)
        db = self.db()
        user = db.execute("SELECT id, is_demo FROM users").fetchone()
        self.assertEqual(user["is_demo"], 1)
        self.assertEqual(len(SqliteTrips(db, user["id"]).all()), 12)

    def test_the_list_shows_accounts_trips_and_demo_marks_but_no_secrets(self):
        self.run_tool("create-user", "alice", "--generate")
        password = re.search(r"Password \(shown once\): (\S+)", self.text).group(1)
        self.run_tool("create-user", "demo1", "--generate", "--with-sample-trips")
        self.run_tool("users")
        self.assertRegex(self.text, r"alice\s+created .* 0 trips")
        self.assertRegex(self.text, r"demo1\s+created .* 12 trips\s+\(demo\)")
        for secret in (password, "scrypt$", "pw_hash"):
            self.assertNotIn(secret, self.text)

    def test_resetting_a_password_signs_the_account_out_everywhere(self):
        self.run_tool("create-user", "alice", "--generate")
        before = accounts.get_user(self.db(), 1)["session_epoch"]
        self.assertEqual(self.run_tool("set-password", "alice", passwords=["a new password", "a new password"]), 0)
        self.assertEqual(accounts.get_user(self.db(), 1)["session_epoch"], before + 1)
        self.assertEqual(self.run_tool("set-password", "nobody", "--generate"), 1)

    def test_deleting_asks_first_unless_told_not_to(self):
        self.run_tool("create-user", "alice", "--generate")
        self.assertEqual(self.run_tool("delete-user", "alice", answers=["no"]), 1)
        self.assertEqual(self.db().execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
        self.assertEqual(self.run_tool("delete-user", "alice", answers=["yes"]), 0)
        self.assertEqual(self.db().execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
        self.run_tool("create-user", "bob", "--generate")
        self.assertEqual(self.run_tool("delete-user", "bob", "--yes"), 0)
        self.assertEqual(self.run_tool("delete-user", "bob", "--yes"), 1)  # already gone

    def test_an_empty_list_says_so(self):
        self.run_tool("users")
        self.assertIn("No accounts yet", self.text)


class TestBackupAndCache(Base):
    def test_a_backup_is_a_working_copy_made_where_asked(self):
        self.run_tool("create-user", "alice", "--generate")
        target = self.path.parent / "elsewhere" / "copy.sqlite"
        self.assertEqual(self.run_tool("backup", str(target)), 0)
        self.assertIn("Backup written", self.text)
        copy = app_db.connect(target)
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT username FROM users").fetchone()[0], "alice")

    def test_the_cache_can_be_counted_and_emptied(self):
        from src.c3_data_adapter import SqliteCache

        cache = SqliteCache(self.path)
        cache.put("suggest", "a", {"places": []})
        cache.close()
        self.run_tool("cache-stats")
        self.assertIn("suggest 1", self.text)
        self.run_tool("clear-cache")
        self.run_tool("cache-stats")
        self.assertIn("suggest 0", self.text)

    def test_every_command_has_help_and_the_tool_needs_a_command(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            manage.main([])
        for sub in ("create-invite", "create-user", "set-password", "backup"):
            with self.assertRaises(SystemExit) as caught, mock.patch("sys.stdout"):
                manage.main([sub, "--help"])
            self.assertEqual(caught.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
