# ADR 0012: The plan path calls the services concurrently, with a name cache, deadlines and a labelled fallback

Status: **Accepted and merged into main in pull request #31 (merge commit 4f0218e, 2026-11-21 20:50 UTC)** (decision date: 2026-11-22).

## Context

Chapter 10 measured the running plan page: with connections to the forecast and routing services closed, only 8.3% of 12 runs with live routes were within the 3 s of requirement 3.4.2.1. Its decision table (D5 to D9) recommended enforcing the 1.0 s weather timeout, keeping connections warm and calling the services concurrently, from a simulation and a replay. None was built, and which change should carry the weight, or whether queued handling would do better, was open. This record resolves it with a swing weight trade-off (report `docs/ch11/EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx`, Sections 2 to 5) on measurements against the live services (`docs/ch11/spike/`, `docs/ch11/data/`).

## Alternatives

| | Alternative | What it would require |
|---|---|---|
| A | Sequential dispatch (the Chapter 10 build) | Nothing |
| B | Concurrent dispatch | One pool call site in `plan.py` |
| C | B plus keep-alive | A loop holding three connections to the routing service and one to the forecast service; 4,320 forecast calls a day more |
| D | B plus a name cache | A cache module, a connection class, a start-up call |
| E | Queued asynchronous handling | A queue and worker, a job table, a status endpoint, a polling script, three new states to check for accessibility |

## Criteria, measures and scores

| Criterion | Weight | A | B | C | D | E |
|---|---|---|---|---|---|---|
| EC.1 Result time when connections must be re-opened (share of plans within 3 s (%)) | 0.238 | 12.5 | 12.5 | 100 | 100 | 12.5 |
| EC.2 Typical result time (median plan response, warm (s)) | 0.071 | 0.187 | 0.162 | 0.162 | 0.162 | 0.414 |
| EC.3 Time to first feedback (submit to first visible response (s)) | 0.167 | 3.61 | 3.61 | 0.138 | 0.534 | 0.003 |
| EC.4 Moving parts to build and verify (count of new threads, loops, endpoints, stores, scripts) | 0.167 | 0 | 1 | 2 | 3 | 6 |
| EC.5 New states to check for accessibility (count of new interaction states) | 0.238 | 0 | 0 | 0 | 0 | 3 |
| EC.6 Headroom under the free service limits (share of Open-Meteo free daily limit used (%)) | 0.119 | 10 | 10 | 53.2 | 10 | 10 |
| **Effectiveness score (0 to 100)** | | **61.1** | **58.4** | **87.5** | **87.6** | **42.7** |
| Life cycle cost over 3 years (assumed $75 an hour) | | $0 | $1,350 | $2,400 | $2,700 | $9,600 |

Swing weights: importance is the team's judgment, variation is computed from the value scores (matrix in the report, Table 8). Measures: EC.1 and EC.3 from 8 timed requests per alternative 120 s apart (`dispatch_gap_*.csv`), E replayed on B with a 0.5 s poll; EC.2 from warm runs; EC.4 and EC.5 design counts; EC.6 from an assumed 500 plans and 500 confirmations a day against Open-Meteo's published free limit of 10,000 calls a day.

## Decision

Select **D: Concurrent dispatch with name cache**, ranked D 87.6, C 87.5, A 61.1, B 58.4, E 42.7, and add the guardrail of Chapter 12 for risk TR.16:

- `src/c2_application_service/plan.py`: `DISPATCH = "concurrent"` starts the forecast call on a pool thread as soon as the start place is known; `WEATHER_DEADLINE_S` (1.0 s, requirement 5.4.4) drops a forecast that is late, and the recommendation says weather rules were not applied; `dispatch_stats()` counts plans, forecasts used, missed and failed.
- `src/c3_data_adapter/route_adapter.py`: `ROUTE_DEADLINE_S` (1.2 s, requirement 5.5.3) gives a labelled estimate for a route that has not arrived; the late call finishes on its own thread so its connection returns to the pool; the pool has room for the late calls.
- `src/c3_data_adapter/dns_cache.py` caches the two hosts' addresses (refreshed in the background after 60 s, not served after 10 min); `route_adapter._CachedHTTPSConnection` connects to the cached address and still verifies the certificate for the host name; `main_web` fills the cache at start-up.
- `DISPATCH = "sequential"` and `USE_DNS_CACHE = False` remain as switches so that the other alternatives can be remeasured; `keepalive.py` exists and is not started.

We built a **guardrail** (the deadlines prevent a missed limit) and a **fallback** (the labelled estimate contains what prevention costs).

## Validation after the change

Connections closed before each run, live directions requests, 2 sides alternating (`docs/ch11/spike/validate_final.py`):

| Side | n | Median (s) | Max (s) | Within 3 s |
|---|---|---|---|---|
| As built | 10 | 6.84 | 8.00 | 0% |
| After the change | 10 | 0.71 | 0.80 | 100% |

## What the other alternatives would have required

- **A:** nothing to build, and a first request that meets two new connections costs the sum of two name lookups (6.9 s measured).
- **B alone:** the longer lookup is still about 3.6 s, so every cold plan misses 3 s (measured 0% within 3 s with 120 s between requests).
- **C:** a loop, a free-limit budget (4,320 more forecast calls a day, about half the free limit with the assumed volume) and services that keep an idle connection. It measured as well as D on the 3 s limit and faster (0.14 s against 0.53 s), and scored within 0.1 point of D; the idle-survival spike, however, found the second call slow in 8 of 14 trials at idle times from 5 s, and a 60 s interval, which would turn the score towards C, was not measured.
- **E:** the queue, the worker, the job table, the status endpoint, the polling script and the accessibility checks of a status page, for the same lookup: it moves the wait behind a status page, it does not shorten it.

## Consequences

- Tests: `tests/test_dispatch_guardrail.py` and `tests/test_dns_cache.py` (concurrency, slow-service failure path, counters, staleness, bad cached address, certificate check); the existing 420 tests pass unchanged.
- The cause measured here is the laptop's resolver (21 of 24 trials took 3.05 to 3.09 s for the name lookup). The deployed host will differ; measure there (30 or more cold runs) before the pilot (Chapter 10 decision D9). If the lookup there is fast, D costs nothing and changes nothing.
- A cached address is not trusted for itself: the certificate is checked against the host name, and a failed connect drops the entry and falls back to an ordinary lookup.
- Unmeasured: the routing directions in the gap condition (replaced by a no-quota root request to the same host); the deployed host.

## Evidence that would change this decision

- A deployed host whose resolver is fast and whose idle connections survive: then B is enough.
- Requirement 3.4.2.1 changing from the page time to a first-feedback time, which favours E.
- The free services dropping their limits or terms (TR.11, TR.21).

