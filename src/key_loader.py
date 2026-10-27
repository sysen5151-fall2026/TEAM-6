"""Find the OpenRouteService key when the server starts.

A Windows user variable set after a terminal (or the app that opened it) started is
not visible to that terminal. So besides the process environment, look in a local
`.env` file (ignored by git) and in the Windows user environment.

Only the entry point calls this; the library code reads os.environ alone, so tests
stay independent of whatever key is stored on the machine. The key is never printed.
"""

import os
from pathlib import Path

NAME = "ORS_API_KEY"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _from_env_file(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and key.strip() == NAME:
            return value.strip().strip('"').strip("'")
    return ""


def _from_windows_user_env() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
            value, _kind = winreg.QueryValueEx(reg, NAME)
        return str(value).strip()
    except OSError:
        return ""


def load_ors_key(env=None, env_file: Path = ENV_FILE, windows_lookup=_from_windows_user_env) -> str:
    """Make ORS_API_KEY available in `env` and return where it came from ("" if nowhere)."""
    env = os.environ if env is None else env
    if env.get(NAME, "").strip():
        return "process environment"
    for source, find in ((".env file", lambda: _from_env_file(env_file)), ("Windows user environment", windows_lookup)):
        value = find()
        if value:
            env[NAME] = value
            return source
    return ""
