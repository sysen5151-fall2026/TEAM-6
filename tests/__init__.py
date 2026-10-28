"""Tests for the walking skeleton and the web pages.

The transit index is pointed at a file that does not exist, so no test depends on whatever
real TCAT data happens to be built on the machine running them. Tests that need a feed
build the invented one in tests/gtfs_fixture.py.
"""

import os
import tempfile

os.environ["ECOCOMMUTE_SECRET"] = "test-secret-not-for-real-use"  # so no key file is written
os.environ["ECOCOMMUTE_DB"] = os.path.join(tempfile.gettempdir(), "ecocommute-tests-unused", "app.sqlite")
os.environ["TCAT_DB"] = os.path.join(tempfile.gettempdir(), "ecocommute-tests-no-transit-index.sqlite")

# Password hashing is deliberately slow; the tests use a cheap setting so they stay fast. One test
# checks that the real setting is the one the application uses.
from src.c2_application_service import accounts  # noqa: E402

accounts.SCRYPT = {"n": 2**10, "r": 8, "p": 1}
