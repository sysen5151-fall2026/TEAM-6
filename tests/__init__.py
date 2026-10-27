"""Tests for the walking skeleton and the web pages.

The transit index is pointed at a file that does not exist, so no test depends on whatever
real TCAT data happens to be built on the machine running them. Tests that need a feed
build the invented one in tests/gtfs_fixture.py.
"""

import os
import tempfile

os.environ["TCAT_DB"] = os.path.join(tempfile.gettempdir(), "ecocommute-tests-no-transit-index.sqlite")
