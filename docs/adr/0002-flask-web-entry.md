# ADR 0002: Flask for the web entry

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27).

## Context

ADR 0001 kept the walking skeleton on the Python standard library and deferred the web framework to the increment that implements the real C.1. The team now wants a working web page for the final demonstration, and later increments (map and route lookups, achievements, a shared goal) need a real web layer.

## Decision

Add a **Flask** page as the web entry of C.1 (`src/c1_web_front_end/web_app.py`, started with `python -m src.main_web`). It collects the Entry Form fields, validates them, hands a `CommuteRequest` to C.2 through `submit_commute_request` and renders the `CommuteImpactResult`. C.2, C.3 and C.4 are unchanged; no calculation or rule lives in the web layer.

Flask is the only non-standard dependency. The CLI skeleton (`python -m src.main`) and its tests still run on the standard library alone; the web tests skip themselves when Flask is not installed.

## Reasons

- Page rendering, form handling and later JSON endpoints take far less code than with `http.server`.
- Python stays the single language, so the team's existing C.2-C.4 code is reused as is.
- The framework is replaceable: only C.1 imports it.

## Consequences

- `pip install -r requirements.txt` is now needed to run the web page (a virtual environment is recommended).
- Trips are still held in memory (C.3 stub), so they reset when the server restarts and are shared by all visitors; persistence is a later increment.
- The factors on the page are still the placeholder values from C.3; the page shows that source label unchanged.
- Requirements 2.1.1 (timing) and 2.5.3 can now be exercised against a real page, but are not yet tested here.

## Evidence that would change this decision

- The instructor requires a different stack for the final demonstration.
- Hosting (X.5) rules out a Python server process.
