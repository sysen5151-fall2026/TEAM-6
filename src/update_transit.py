"""Download the TCAT GTFS feed and build the local transit index.

    python -m src.update_transit                 # download the agency's current feed, then build
    python -m src.update_transit --zip FILE.zip  # build from a zip you already have

The raw feed and the index live in data/tcat/ (ignored by git: the agency's terms for
redistributing the data were not found, so it is not committed). Nothing in the zip is
extracted or run.
"""

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from src.c3_data_adapter.gtfs_store import DB_PATH, FEED_URL, FeedError, build_database

MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
TIMEOUT_S = 60


def download(url: str, target: Path) -> int:
    """Fetch the feed to `target` (a temporary file renamed on success). Returns the size in bytes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    size = 0
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp, open(partial, "wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise FeedError("The download is larger than 100 MB; refusing it.")
                out.write(chunk)
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return size


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the local TCAT transit index.")
    parser.add_argument("--zip", help="use this GTFS zip instead of downloading")
    parser.add_argument("--url", default=FEED_URL, help="feed address (default: the TCAT feed)")
    args = parser.parse_args(argv)

    zip_path = Path(args.zip) if args.zip else DB_PATH.parent / "tcat-ny-us.zip"
    try:
        if not args.zip:
            print(f"Downloading {args.url} ...")
            print(f"  {download(args.url, zip_path):,} bytes saved to {zip_path}")
        result = build_database(zip_path)
    except (FeedError, OSError, urllib.error.URLError) as err:
        print(f"Could not update the transit data: {err}", file=sys.stderr)
        return 1

    feed, counts = result["feed"], result["counts"]
    print(f"Built {DB_PATH}")
    print(f"  {feed['agency']} | feed version {feed['version']} | service {feed['start_date']} to {feed['end_date']}")
    print("  " + ", ".join(f"{n:,} {t.replace('_', ' ')}" for t, n in counts.items()))
    print(f"  shape distances are in {'feet' if abs(result['unit_m'] - 0.3048) < 1e-6 else 'units of ' + str(result['unit_m']) + ' m'}"
          " (detected from the geometry)")
    if any(result["skipped"].values()):
        print(f"  skipped unreadable rows: {result['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
