"""Key lookup at server start. No real key or registry is touched.

Run:  python -m unittest discover -s tests -t .
"""

import tempfile
import unittest
from pathlib import Path

from src.key_loader import NAME, load_ors_key


def write_env(text: str) -> Path:
    folder = tempfile.mkdtemp()
    path = Path(folder) / ".env"
    path.write_text(text, encoding="utf-8")
    return path


class TestKeyLoader(unittest.TestCase):
    def test_process_environment_wins_and_is_left_alone(self):
        env = {NAME: "from-process"}
        source = load_ors_key(env, write_env(f"{NAME}=from-file"), lambda: "from-windows")
        self.assertEqual((source, env[NAME]), ("process environment", "from-process"))

    def test_env_file_is_read_before_windows(self):
        env = {}
        source = load_ors_key(env, write_env(f'# note\nOTHER=1\n{NAME} = "from-file"\n'), lambda: "from-windows")
        self.assertEqual((source, env[NAME]), (".env file", "from-file"))

    def test_windows_user_environment_is_the_last_resort(self):
        env = {}
        source = load_ors_key(env, Path("does-not-exist.env"), lambda: "from-windows")
        self.assertEqual((source, env[NAME]), ("Windows user environment", "from-windows"))

    def test_nothing_found_leaves_the_environment_untouched(self):
        env = {NAME: "   "}
        self.assertEqual(load_ors_key(env, Path("does-not-exist.env"), lambda: ""), "")
        self.assertEqual(env, {NAME: "   "})

    def test_the_real_env_file_path_is_not_tracked_by_git(self):
        ignore = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", [line.strip() for line in ignore])


if __name__ == "__main__":
    unittest.main()
