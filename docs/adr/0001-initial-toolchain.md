# ADR 0001: Initial toolchain for the walking skeleton

Status: **Proposed - needs team review and merge approval** (date: 2026-10-05).

## Context

The EcoCommute Product Description names Next.js, SQLite, Open-Meteo and Vercel. The team repository was started from a Python scaffold and most team members are more comfortable with Python. Milestone 1 only needs one stubbed end-to-end path for UC.1 (no real source access, live model calls, retries, error handling or logging).

## Decision

Use **Python 3.12, standard library only** for the walking skeleton: plain modules per asset (C.1-C.4, plus a simulated X.1 and a stubbed X.3) and `unittest` for tests. Defer the web framework, persistence and hosting choices to the increment that implements the real C.1 and C.3.

## Reasons

- Lowest setup cost: no installs, same command on every teammate's machine.
- The skeleton's value is the correct participants and call order from the model, not the web stack.
- The calculation and rule logic in C.2 is stack-independent, so it carries over to any later framework.

## Consequences

- The product description's stack is not yet satisfied; there is no web UI (requirements 2.1.1 timing, 2.1.9 and 2.5.3 cannot be tested yet).
- A later web layer (for example FastAPI or Flask with SQLite, or the originally planned Next.js) needs a new ADR; the BMA lifecycle treats hosting as an external enabling service (X.5), so the choice does not change the system boundary.

## Evidence that would change this decision

- The team or instructor requires the product-description stack (Next.js / Vercel) for the pilot.
- The Milestone 2 increment needs a deployed web UI that the Python standard library cannot reasonably serve.
- A Python-capable teammate shortage appears, or the team prefers one language for front end and back end.
