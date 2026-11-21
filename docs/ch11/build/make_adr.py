"""Write docs/adr/0012-plan-path-dispatch.md from docs/ch11/data/analysis.json, so the record and the report agree.

    python docs/ch11/build/make_adr.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
A = json.load(open(os.path.join(ROOT, "docs", "ch11", "data", "analysis.json"), encoding="utf-8"))
SEL = A["selected"]
NAMES = {"A": "Sequential dispatch (as built)", "B": "Concurrent dispatch", "C": "Concurrent dispatch with keep-alive",
         "D": "Concurrent dispatch with name cache", "E": "Queued asynchronous handling"}
RANK = sorted(A["totals"], key=lambda k: -A["totals"][k]["score"])
ST = A["measured"]["gap_stats"]
RAW = A["raw"]
FV = os.path.join(ROOT, "docs", "ch11", "data", "final_validation.json")
fv = json.load(open(FV, encoding="utf-8"))["summary"] if os.path.exists(FV) else None

TITLE = {"A": "The plan path stays sequential; deadlines and a labelled fallback are added",
         "B": "The plan path calls the services concurrently, with deadlines and a labelled fallback",
         "C": "The plan path calls the services concurrently, with a keep-alive, deadlines and a labelled fallback",
         "D": "The plan path calls the services concurrently, with a name cache, deadlines and a labelled fallback",
         "E": "The plan path is queued and polled, with deadlines and a labelled fallback"}
MECH = {"A": "", "B": "", "C": "- `src/c3_data_adapter/keepalive.py` keeps one connection open to the forecast service and three to the routing service with a request every 20 s; started by `main_web`.\n",
        "D": "- `src/c3_data_adapter/dns_cache.py` caches the two hosts' addresses (refreshed in the background after 60 s, not served after 10 min); `route_adapter._CachedHTTPSConnection` connects to the cached address and still verifies the certificate for the host name; `main_web` fills the cache at start-up.\n",
        "E": ""}[SEL]

lines = [
    "# ADR 0012: " + TITLE[SEL],
    "",
    "Status: **Proposed - needs team review and merge approval** (date: 2026-11-22). Implemented on branch `docs/ch10-modeling-simulation`; not yet merged.",
    "",
    "## Context",
    "",
    "Chapter 10 measured the running plan page: with connections to the forecast and routing services closed, only 8.3% of 12 runs with live routes were within the 3 s of requirement 3.4.2.1. "
    "Its decision table (D5 to D9) recommended enforcing the 1.0 s weather timeout, keeping connections warm and calling the services concurrently, from a simulation and a replay. None was built, and which change should carry the weight, or whether queued handling would do better, was open. "
    "This record resolves it with a swing weight trade-off (report `docs/ch11/EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx`, Sections 2 to 5) on measurements against the live services (`docs/ch11/spike/`, `docs/ch11/data/`).",
    "",
    "## Alternatives",
    "",
    "| | Alternative | What it would require |",
    "|---|---|---|",
    "| A | Sequential dispatch (the Chapter 10 build) | Nothing |",
    "| B | Concurrent dispatch | One pool call site in `plan.py` |",
    "| C | B plus keep-alive | A loop holding three connections to the routing service and one to the forecast service; 4,320 forecast calls a day more |",
    "| D | B plus a name cache | A cache module, a connection class, a start-up call |",
    "| E | Queued asynchronous handling | A queue and worker, a job table, a status endpoint, a polling script, three new states to check for accessibility |",
    "",
    "## Criteria, measures and scores",
    "",
    "| Criterion | Weight | " + " | ".join(f"{k}" for k in "ABCDE") + " |",
    "|---|---|" + "---|" * 5,
]
for w in A["weights"]:
    lines.append(f"| {w['id']} {w['name']} ({w['unit']}) | {w['weight']:.3f} | " + " | ".join(f"{RAW[k][w['id']]:.3g}" for k in "ABCDE") + " |")
lines += [
    "| **Effectiveness score (0 to 100)** | | " + " | ".join(f"**{A['totals'][k]['score']:.1f}**" for k in "ABCDE") + " |",
    "| Life cycle cost over 3 years (assumed $75 an hour) | | " + " | ".join(f"${A['lcc'][k]['total']:,.0f}" for k in "ABCDE") + " |",
    "",
    "Swing weights: importance is the team's judgment, variation is computed from the value scores (matrix in the report, Table 8). Measures: EC.1 and EC.3 from 8 timed requests per alternative 120 s apart (`dispatch_gap_*.csv`), E replayed on B with a 0.5 s poll; EC.2 from warm runs; EC.4 and EC.5 design counts; EC.6 from an assumed 500 plans and 500 confirmations a day against Open-Meteo's published free limit of 10,000 calls a day.",
    "",
    "## Decision",
    "",
    f"Select **{SEL}: {NAMES[SEL]}**, ranked " + ", ".join(f"{k} {A['totals'][k]['score']:.1f}" for k in RANK) + ", and add the guardrail of Chapter 12 for risk TR.16:",
    "",
    "- `src/c2_application_service/plan.py`: `DISPATCH = \"concurrent\"` starts the forecast call on a pool thread as soon as the start place is known; `WEATHER_DEADLINE_S` (1.0 s, requirement 5.4.4) drops a forecast that is late, and the recommendation says weather rules were not applied; `dispatch_stats()` counts plans, forecasts used, missed and failed.",
    "- `src/c3_data_adapter/route_adapter.py`: `ROUTE_DEADLINE_S` (1.2 s, requirement 5.5.3) gives a labelled estimate for a route that has not arrived; the late call finishes on its own thread so its connection returns to the pool; the pool has room for the late calls.",
    MECH.rstrip("\n"),
    "- `DISPATCH = \"sequential\"` and `USE_DNS_CACHE = False` remain as switches so that the other alternatives can be remeasured; `keepalive.py` exists and is not started.",
    "",
    "We built a **guardrail** (the deadlines prevent a missed limit) and a **fallback** (the labelled estimate contains what prevention costs).",
    "",
]
if fv:
    lines += ["## Validation after the change", "", "Connections closed before each run, live directions requests, 2 sides alternating (`docs/ch11/spike/validate_final.py`):", "",
              "| Side | n | Median (s) | Max (s) | Within 3 s |", "|---|---|---|---|---|"]
    for k, v in fv.items():
        lines.append(f"| {'As built' if k == 'asbuilt' else 'After the change'} | {v['n']} | {v['median']:.2f} | {v['max']:.2f} | {100 * v['within_3s']:.0f}% |")
    lines.append("")
lines += [
    "## What the other alternatives would have required",
    "",
    "- **A:** nothing to build, and a first request that meets two new connections costs the sum of two name lookups (6.9 s measured).",
    "- **B alone:** the longer lookup is still about 3.6 s, so every cold plan misses 3 s (measured 0% within 3 s with 120 s between requests).",
    "- **C:** a loop, a free-limit budget (4,320 more forecast calls a day, about half the free limit with the assumed volume) and services that keep an idle connection. It measured as well as D on the 3 s limit and faster (0.14 s against 0.53 s), and scored within 0.1 point of D; the idle-survival spike, however, found the second call slow in 8 of 14 trials at idle times from 5 s, and a 60 s interval, which would turn the score towards C, was not measured.",
    "- **E:** the queue, the worker, the job table, the status endpoint, the polling script and the accessibility checks of a status page, for the same lookup: it moves the wait behind a status page, it does not shorten it.",
    "",
    "## Consequences",
    "",
    "- Tests: `tests/test_dispatch_guardrail.py` and `tests/test_dns_cache.py` (concurrency, slow-service failure path, counters, staleness, bad cached address, certificate check); the existing 420 tests pass unchanged.",
    "- The cause measured here is the laptop's resolver (21 of 24 trials took 3.05 to 3.09 s for the name lookup). The deployed host will differ; measure there (30 or more cold runs) before the pilot (Chapter 10 decision D9). If the lookup there is fast, D costs nothing and changes nothing.",
    "- A cached address is not trusted for itself: the certificate is checked against the host name, and a failed connect drops the entry and falls back to an ordinary lookup.",
    "- Unmeasured: the routing directions in the gap condition (replaced by a no-quota root request to the same host); the deployed host.",
    "",
    "## Evidence that would change this decision",
    "",
    "- A deployed host whose resolver is fast and whose idle connections survive: then B is enough.",
    "- Requirement 3.4.2.1 changing from the page time to a first-feedback time, which favours E.",
    "- The free services dropping their limits or terms (TR.11, TR.21).",
    "",
]
with open(os.path.join(ROOT, "docs", "adr", "0012-plan-path-dispatch.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print("wrote ADR 0012, selected", SEL)
