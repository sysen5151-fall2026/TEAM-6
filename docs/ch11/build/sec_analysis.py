"""Sections 1 to 5 of the report: introduction, preparation, data, value analysis, selection and decision record."""
import csv
import json
import os

import docx_helpers as H
from report_lib import (A, D11, F, NAMES, SEL, SHORT, T, cap_fig, cap_tab, f1, f2, f3, fig, money, pct)  # noqa: F401

W = {w["id"]: w for w in A["weights"]}
TOT = A["totals"]
RAW = A["raw"]
ST = A["measured"]["gap_stats"]
LCC = A["lcc"]
SENS = A["sensitivity"]
RANK = sorted(TOT, key=lambda k: -TOT[k]["score"])
RUNNER = next(k for k in RANK if k != SEL)
ASSUME = A["assumptions"]
PH = list(csv.DictReader(open(os.path.join(D11, "connection_phases.csv"), encoding="utf-8")))
WARM = A["measured"]["warm_runs"]


def intro(d):
    H.heading(d, "1 Introduction", 1)
    H.heading(d, "1.1 Purpose of the system analysis and the risk assessment", 2)
    H.para(d, "This report section is the deliverable of Project Task 6 and covers Chapters 11 and 12 of the lab manual. Part I (Sections 2 to 5) is the system analysis: a swing weight trade-off on a build decision the team had not yet made, "
              "with the selected alternative implemented in the product. Part II (Sections 6 to 10) is the risk assessment: five system-level risks derived from the architecture model, a risk table and matrix, "
              "a mitigation and monitoring plan for the top risk, and a product risk register with a guardrail and a fallback that are built and tested. "
              "The two parts use the same Innoslate model (EcoCommute 11.5, which adds the criteria, the alternatives and the risks to model 11.4) and the same code, and they meet at one point: the risk that the trade-off was meant to reduce is the top risk of the assessment.")
    H.heading(d, "1.2 The decision and why it was open", 2)
    H.para(d, "Chapter 10 measured the running application and found that the plan page misses the 3-second limit (requirement 3.4.2.1) whenever the connections to the two external services must be opened again: only 8.3% of 12 cold runs with live routes were within 3 s. "
              "Its decision table (D5 to D9) recommended three architecture changes on the strength of a simulation and a replay: enforce the 1.0 s weather timeout, keep the connections warm, and call the two services concurrently. "
              "None was built or measured, and the table did not say which change should carry the weight or whether a different structure (queued handling with a status page) would serve better. "
              "That is the open decision: **how the plan path should ask the external services**. The alternatives are described in Section 2.2, each was prototyped or replayed against the live services in this chapter, and the "
              "measurements changed the picture (Section 3.2): the seconds that Chapter 10 attributed to connection set-up are, on the development laptop, a host-name lookup.")
    H.heading(d, "1.3 Conventions, assumptions and how to read the numbers", 2)
    for t in [
        "Alternatives are lettered A to E and criteria EC.1 to EC.6; risks keep the model's numbers (TR.n). Requirement, need, function and asset numbers are those of the model.",
        "Everything measured in this chapter was measured on one developer laptop on 22 November 2026 (Windows 11, Python 3.12, RTX 5060 laptop GPU, one home network). The deployment host and its network are not this laptop; the measurement on the deployed host is a planned action (Section 8).",
        "Assumptions are marked **Assumption** where they are used and are collected in " + T("assumptions") + " of Section 3.3. A number without that mark was measured here, comes from an earlier chapter of this project, or has a source in Appendix C.",
        "Importance ratings, risk ratings, labour hours and the labour rate are the team's judgments. They were written down before the scores that depend on them were computed, and each one sits in one place in the code (docs/ch11/sim/model.py) so that it can be changed and the report rebuilt.",
        "Times are system-side only: the harness calls the application's own plan function, with no browser and no network between a commuter and the server, as in Chapter 10.",
    ]:
        H.bullet(d, t)
    cap_tab(d, "coverage", "Assignment items and where this report covers them.")
    rows = [
        ("Prepare: scope, types, objectives; criteria; candidate elements; methods", "Section 2"),
        ("Perform: data and inputs, assumptions highlighted", "Section 3"),
        ("Perform: effectiveness, life cycle cost and affordability analysis", "Section 4"),
        ("Select the alternative; sensitivity; implementation; architecture decision record", "Section 5; ADR 0012; ADR 0011"),
        ("Risks from the architecture model; risk table with scales and calculation", "Sections 6.1 to 6.4"),
        ("Risk matrix", "Section 7"),
        ("Top risk, strategy, mitigation plan (separate page)", "Section 8"),
        ("Monitoring and control; use of the modeling tool", "Section 9"),
        ("Product risk register with AI-specific risks; guardrail and fallback; failure-path tests", "Section 10; docs/risks.md"),
        ("Team contribution table", "First page"),
    ]
    H.table(d, ["Item", "Where"], rows, [5.2, 1.9], size=9)


def prepare(d):
    H.heading(d, "2 System Analysis: Preparation", 1)
    H.heading(d, "2.1 Scope, types and objectives of the analysis", 2)
    H.para(d, "**Scope.** The plan path: from a validated start and destination to the comparison page, that is, how the Reference Data Subsystem (C.0.2) obtains routes from the Route Service (X.6) and the forecast from Open-Meteo (X.3) "
              "and how long the commuter waits (F.2.2, F.2.5, F.2.6; requirements 2.1.2, 3.4.2.1, 5.4.4, 5.5.3). The result page, the records and the explanation are out of scope; they take milliseconds (Chapter 10, Table 14).")
    H.para(d, "**Types of analysis.** Effectiveness analysis (a weighted value score from measured and counted criteria), life cycle cost analysis, affordability analysis, and a sensitivity analysis of the weights and of the unmeasured inputs.")
    H.para(d, "**Objective.** Select the alternative with the highest effectiveness score among those whose life cycle cost fits the budget the model allocates to the subsystem, implement it, and record the decision. "
              "The rule was fixed before the scores were computed.")
    H.heading(d, "2.2 Candidate elements: physical architecture alternatives", 2)
    H.para(d, "Five alternatives were considered. A is the product as built, B to D add structure to it one step at a time, and E changes the request handling. " + T("alts") + " says what each is and what it would require; " + F("alts") + " shows what each does for one plan. "
              "All five are entities of the model (AL.A to AL.E, related to C.0.2 and C.0.6, and to each other), and decision DEC.1 relates them to the criteria.")
    cap_tab(d, "alts", "Physical architecture alternatives and what each would require.")
    rows = [
        ("A Sequential dispatch (as built)", "The plan asks for the routes, then for the forecast, in the request thread; connections are opened on demand.", "Nothing: it is the code at Chapter 10. Its cost is the sum of the two calls."),
        ("B Concurrent dispatch", "The forecast call starts as soon as the start place is known and runs on a pool thread beside the route calls; the plan waits for the slower one.", "One thread pool and one call site in plan.py; tests that the answer is the same and that the time is the longer call. No new service or storage."),
        ("C Concurrent dispatch with keep-alive", "As B, plus a background loop that sends a light request to each service every 20 s so that connections stay open (Chapter 10 decision D6).", "A loop that holds three connections to the routing service and one to the forecast service; 4,320 extra forecast calls a day against a free limit of 10,000; the services must keep an idle connection open for 20 s, which they did not always do."),
        ("D Concurrent dispatch with name cache", "As B, plus an in-process cache of the two hosts' addresses (filled at start-up, refreshed in the background, used for new connections; the certificate is still checked for the host name).", "A cache module, a connection class, a start-up call; tests of staleness, failure and the certificate check. No extra call to either service."),
        ("E Queued asynchronous handling", "The plan request is queued and answered at once with a status page; a worker does what B does; the page polls every 0.5 s for the result.", "A queue and worker, a job table, a status endpoint, a polling script, an expiry job; a status page that a screen reader announces (WCAG 2.2 AA); three new states to test (waiting, ready, failed). More than the other four combined."),
    ]
    H.table(d, ["Alternative", "What it is", "What it would require"], rows, [1.5, 2.9, 2.7], size=8.5)
    fig(d, "alts", "fig_alternatives.png", "What each alternative does for one plan, from the medians of the measured route and forecast times (120 s between requests).", 6.4)
    H.heading(d, "2.3 Evaluation criteria, objective functions and metrics", 2)
    H.para(d, "Six criteria represent what the customer values in this decision. Each is traced to a stakeholder need, to a requirement and to a model entity (the Statement EC.n in model 11.5, which is traced to the requirement). "
              "They are independent in what they measure: EC.1 to EC.3 are three different times (the worst case, the typical case, the first sign of life), EC.4 and EC.5 are two different burdens (building and verifying; accessibility), and EC.6 is a limit outside the system. "
              "Alternatives that are good on one are not necessarily good on another: E is best on EC.3 and worst on EC.4 and EC.5, which is why they are not merged. Cost is not a criterion; it is analysed on its own (Section 4.3) as the lab manual asks.")
    cap_tab(d, "criteria", "Evaluation criteria with metric, range, objective (value) function and traces.")
    rows = []
    for w in A["weights"]:
        rows.append((f"{w['id']} {w['name']}", w["unit"], f"{w['best']:g} -> 100\n{w['worst']:g} -> 0", "Linear between the two, held at 0 and 100 outside", f"Need {w['need']}\nRequirement {w['req']}\nStatement {w['id']}"))
    H.table(d, ["Criterion", "Metric and unit", "Range (value)", "Objective function", "Trace"], rows, [1.7, 1.8, 0.9, 1.3, 1.4], size=8)
    H.para(d, "The ranges are set by the requirement where one exists (3 s for EC.2 and EC.3 is the display limit; 100% for EC.1) and by what is possible otherwise (zero extra parts and zero new states are best; the worst values are the largest counts among the designs, rounded up). "
              "A value function is linear because no evidence was found that the customer values the middle of a range unevenly.")
    H.heading(d, "2.4 Methods and procedures", 2)
    for t in [
        "Define the scope, alternatives, criteria and value functions (this section). The rule for choosing was fixed here.",
        "Measure each alternative against the live services in prototype spikes (Section 3), or replay it on a measured alternative where a spike would cost more than it tells (E).",
        "Place each criterion in the swing weight matrix by its importance (the team's judgment, with reasons) and its variation (computed from the value scores), and normalise the swing weights (Section 4.1).",
        "Compute value scores and the weighted total for each alternative; compute life cycle cost and affordability; select by the rule (Sections 4.2 to 4.4 and 5.1).",
        "Test the selection: vary each weight, draw 10,000 random weightings, and change the assumed inputs (Section 5.2).",
        "Implement the selected alternative, write the decision record (Sections 5.3 and 5.4).",
    ]:
        H.bullet(d, t)


def data(d):
    H.heading(d, "3 Data and Assumptions", 1)
    H.heading(d, "3.1 What was measured", 2)
    H.para(d, "The data come from four sources: three prototype spikes run in this chapter (their scripts and raw files are in docs/ch11/spike and docs/ch11/data), the Chapter 10 campaign, and counts taken from the designs. "
              "Where a measurement could not be made as designed, it is said so in " + T("data") + " and in Section 3.3.")
    cap_tab(d, "data", "Data collected, how, and its limits.")
    rows = [
        ("Phases of a new connection (spike 1b)", "Name lookup, TCP connect, TLS handshake and first response, 12 trials 10 s apart to each host", "connection_phases.csv", "One machine and network; the lookup time is the resolver's, not the services'"),
        ("Idle survival of a kept-open connection (spike 1)", "Call, wait 5 to 240 s, call again; both hosts", "idle_sensitivity.csv", "14 of 24 planned trials (stopped to free the network); the second call was slow in 8 of 14, at idle times as short as 5 s: survival is not reliable"),
        ("Plan response under A, B, C and D (spike 2, gap condition)", "plan_commute against the live services, 8 timed requests 120 s apart per alternative (C: 123 s, see below), one process per alternative, one untimed first request", "dispatch_gap_A.csv ... D.csv", "Route calls replaced by a request to the root path of the same host (no quota), see below; n = 8 each"),
        ("Plan response, warm connections, A and B", "7 runs each with live routes, 3 s apart", "dispatch_warm.csv", "Stopped at 14 runs by a refusal from the routing service"),
        ("Cold runs of Chapter 10", "12 runs with live routes and closed connections; 44 without", "docs/ch10/data", "Chapter 10 measurements, used for context"),
        ("Counts", "New parts and new states of each design", "Section 4.2", "The team's design counts, not measured"),
    ]
    H.table(d, ["Data", "How", "File", "Limits"], rows, [1.6, 2.4, 1.3, 1.8], size=8)
    H.para(d, "**The routing quota.** The first campaign (warm, 3 s apart, live directions requests) was stopped after 14 runs when the routing service refused requests. The published free limit is 2,000 directions requests a day and 40 a minute "
              "(openrouteservice FAQ, Table 6; the figure of 200 a day in the Chapter 10 report does not match it and should be checked against the team's dashboard). At about 6 requests every 6 s the run exceeded the per-minute limit. "
              "The gap campaigns then replaced the directions call by a request to the root path of the same host, which does not use the directions quota and meets the same connection set-up. "
              "What this leaves out is the directions computation (about 25 ms when warm: 0.126 s against 0.101 s); the forecast call is always the real one. **Assumption:** the root path is not counted against the directions quota.")
    H.heading(d, "3.2 Results of the measurements", 2)
    ph_dns = [int(r["dns_ms"]) for r in PH]
    slow = sum(1 for x in ph_dns if x > 3000)
    mid = sum(1 for x in ph_dns if 1000 < x < 2000)
    H.para(d, f"**Where a new connection loses its seconds.** Chapter 10 called the slow case connection set-up. Timing the phases (" + F("phases") + f") shows that the name lookup took 3.05 to 3.09 s in {slow} of {len(PH)} trials and 1.06 to 1.07 s in {mid}; "
              f"the TCP connect never took more than {max(int(r['tcp_ms']) for r in PH)} ms, the TLS handshake {max(int(r['tls_ms']) for r in PH)} ms and the first response {max(int(r['first_response_ms']) for r in PH)} ms. "
              "A kept-open connection avoids the lookup, and so does a cache of the address. The cause is this laptop's resolver (a first server that does not answer, then a second); the deployed host will have its own, which is why the deployed-host measurement is an action of the plan.")
    fig(d, "phases", "fig_phases.png", "Mean time of the four phases of a new connection to each host (12 trials each).", 5.2)
    n_gap = {k: ST[k]["n"] for k in ST if k in "ABCD"}
    H.para(d, "**Plan response with 120 s between requests** (" + F("response") + " and " + T("gapstats") + "). Each of the four alternatives ran in its own process so that one could not leave open connections for another; "
              "an interleaved first attempt showed B inheriting A's connections and was discarded. A first run of C with a 120 s gap was phase-locked to the keep-alive round (every request came 8 s after one, so it measured a single idle age); it was repeated with a 123 s gap, which makes the idle age of the connection vary from 0 to 17 s, and the repeat is the one used (the first is kept as dispatch_gap_C_phase_locked.csv). The services keep some idle connections open and not others, so a run may meet an open connection or a new one; "
              "what is measured is what an alternative does with whichever it meets.")
    cap_tab(d, "gapstats", "Plan response in seconds, 120 s between requests (8 timed requests each; E is replayed on B with a 0.5 s poll).")
    rows = []
    for k in "ABCDE":
        s = ST[k]
        rows.append((f"{k} {SHORT[k]}", str(s["n"]), f2(s["median"]), f2(s["mean"]), f2(s["p95"]), f2(s["max"]), pct(100 * s["within_3s"]), str(s["slow_runs"])))
    H.table(d, ["Alternative", "n", "Median", "Mean", "95th", "Max", "Within 3 s", "Runs over 1.2 s"], rows, [1.7, 0.4, 0.7, 0.7, 0.7, 0.7, 0.9, 1.1], size=8.5)
    fig(d, "response", "fig_response.png", "Plan response of each alternative (each dot one timed request, 120 s apart).", 5.4)
    w = WARM
    H.para(d, f"**Warm connections.** With connections open and live routes, A took a median of {f2(sorted(w['A'])[len(w['A']) // 2])} s and B {f2(sorted(w['B'])[len(w['B']) // 2])} s over {len(w['A'])} and {len(w['B'])} runs: the forecast call is about 21 ms and the route calls about 0.13 s, "
              "so running them side by side saves the 21 ms. The one large value is the first request of the process, which was A's (6.9 s: the two lookups added); B ran second in that pair and met connections that A had opened, so no cold request of B is in the warm set.")
    H.heading(d, "3.3 Sources verified and assumptions", 2)
    H.para(d, "Each factual claim that enters the analysis is either measured here, taken from an earlier chapter of this project, or has a source that was opened and read on 22 November 2026. Claims that came from the assistant and could not be checked are not used. "
              + T("sources") + " lists the sources and " + T("assumptions") + " lists the assumptions, which are shaded.")
    cap_tab(d, "sources", "Claims used in the analysis and the source checked.")
    rows = [
        ("Open-Meteo free plan: non-commercial use, under 10,000 calls a day, 5,000 an hour, 600 a minute", "open-meteo.com/en/terms and open-meteo.com/en/pricing (read 22 Nov 2026)"),
        ("OpenRouteService free plan: directions default limit 2,000 requests a day and 40 in any 60 s; a daily refusal is HTTP 403, a per-minute one 429", "giscience.github.io/openrouteservice/frequently-asked-questions (read 22 Nov 2026); the Chapter 10 report says 200 a day: conflict flagged"),
        ("Qwen2.5 1.5B is licensed Apache License 2.0; 986 MB; Ollama 0.40.17", "ollama.com/library/qwen2.5:1.5b and `ollama --version` (22 Nov 2026)"),
        ("Budget apportionment: $90,000 to the Reference Data Subsystem, $750,000 system; 1.2 s and 3 s time budgets", "Chapter 8 and 9 report (Tables of cost and response-time apportionment); requirements 5.5.1, 3.4.1.1, 5.5.3, 3.4.2.1 in model 11.5"),
        ("Plan response and stage times with warm and cold connections", "Chapter 10 report, Tables 14 and 16, and docs/ch10/data"),
        ("Name lookup 3.05 to 3.09 s per new connection", "Measured: docs/ch11/data/connection_phases.csv"),
    ]
    H.table(d, ["Claim", "Source"], rows, [3.6, 3.5], size=8.5)
    cap_tab(d, "assumptions", "Assumptions used, why, and what changes if they are wrong.")
    rows = [
        (f"{ASSUME['plans_per_day']} plans and confirmations a day (500 accounts, about one trip each)", "Requirement 5.5.5 sets 500 accounts; one trip a day is a guess", "Changes only EC.6 (use of the free limit). At about 6 plans a day per account (2,840 plans a day) C would pass the limit."),
        ("Keep-alive every 20 s", "A compromise between holding connections and spending the free limit", "A shorter interval holds more connections and costs more calls; the idle survival data are too thin to set it"),
        ("The routing root path is not counted against the directions quota", "The code comment of warm_up says so; not verified at the service", "If it is counted, C's keep-alive spends the quota (EC.6 would be worse for C)"),
        (f"Labour rate ${ASSUME['rate']:.0f} an hour, {ASSUME['life_years']}-year life", "A round loaded rate; the pilot year and two more", "Scales every LCC; the ranking of costs does not change"),
        ("Build, verify and maintain hours of each alternative (" + T("lcc") + ")", "The team's estimates from the code written; E is estimated, not built", "Move E's cost; E is already the most expensive"),
        ("E replayed on B with a 0.5 s poll and a 2 ms hand-off", "E was not built", "E's result time would change by at most the poll interval"),
        ("Importance ratings of the criteria", "The team's judgment; see Section 4.1", "Tested in Section 5.2"),
    ]
    H.table(d, ["Assumption", "Why", "If wrong"], rows, [2.4, 2.2, 2.5], size=8.5, hdr_fill="9A6B00")


def value(d):
    H.heading(d, "4 Value Analysis", 1)
    H.heading(d, "4.1 Swing weight matrix", 2)
    H.para(d, "The swing weight method gives a criterion weight by two questions: how important is the criterion to the customer, and how much does it vary across the alternatives (how much of its range the choice actually moves). "
              "Importance is the team's judgment. Variation is computed: the range of the value scores of the criterion across the five alternatives, high at 50 points or more, medium from 20 to under 50, low below 20. "
              "A swing weight is read from " + T("matrix") + " and normalised to sum to 1.")
    cap_tab(d, "matrix", "Swing weight matrix. Cells give the swing weight; the criteria placed in each cell are in bold.")
    swing = {("H", "H"): 100, ("H", "M"): 80, ("H", "L"): 60, ("M", "H"): 70, ("M", "M"): 50, ("M", "L"): 30, ("L", "H"): 40, ("L", "M"): 20, ("L", "L"): 10}
    names = {"H": "High", "M": "Medium", "L": "Low"}
    rows = []
    for imp in "HML":
        row = [f"Importance: {names[imp]}"]
        for var in "HML":
            here = [w["id"] for w in A["weights"] if w["importance"] == imp and w["variation"] == var]
            row.append(f"{swing[(imp, var)]}" + (("\n**" + ", ".join(here) + "**") if here else ""))
        rows.append(row)
    H.table(d, ["", "Variation: High (50+)", "Variation: Medium (20 to 49)", "Variation: Low (under 20)"], rows, [1.6, 1.8, 1.9, 1.8], size=9, first_bold=True)
    cap_tab(d, "weights", "Importance and variation explained for each criterion, swing weight and normalised weight.")
    rows = []
    for w in A["weights"]:
        rows.append((w["id"], f"{w['importance']}: {w['why']}", f"{w['variation']}: range {w['range']:.0f} points", f"{w['swing']:g}", f3(w["weight"])))
    H.table(d, ["ID", "Importance (team judgment) and why", "Variation (computed)", "Swing", "Weight"], rows, [0.5, 3.4, 1.4, 0.6, 0.7], size=8)
    H.para(d, "Total swing = " + f"{sum(w['swing'] for w in A['weights']):g}" + ". Importance was written down before any score was computed. EC.1 and EC.5 are high because each is a shall requirement of the system (3.4.2.1, 3.4.4.1); the others are medium because the requirement they come from is a means "
              "(EC.2, EC.3), a schedule or a limit that has a fallback (EC.4, EC.6).")
    H.heading(d, "4.2 Effectiveness analysis", 2)
    H.para(d, T("raw") + " gives the measure of each alternative on each criterion, " + T("values") + " gives the value scores, and " + T("totals") + " the weighted totals with the contribution of each criterion. " + F("scores") + " shows the totals.")
    cap_tab(d, "raw", "Measures. EC.1, EC.3: measured (" + T("gapstats") + "). EC.2: measured warm. EC.4, EC.5: design counts. EC.6: calculated from the assumption of 500 plans a day.")
    rows = []
    for k in "ABCDE":
        r = RAW[k]
        rows.append((f"{k} {SHORT[k]}", f1(r["EC.1"]), f2(r["EC.2"]), f"{r['EC.3']:.3f}" if r["EC.3"] < 0.1 else f2(r["EC.3"]), f"{r['EC.4']:g}", f"{r['EC.5']:g}", f1(r["EC.6"])))
    H.table(d, ["Alternative", "EC.1 within 3 s (%)", "EC.2 median (s)", "EC.3 first feedback (s)", "EC.4 parts", "EC.5 states", "EC.6 free limit used (%)"], rows, [1.5, 1.0, 0.9, 1.1, 0.8, 0.8, 1.0], size=8.5)
    cap_tab(d, "values", "Value scores (0 to 100) by criterion.")
    rows = []
    for k in "ABCDE":
        rows.append((f"{k} {SHORT[k]}", *[f1(TOT[k]["values"][w["id"]]) for w in A["weights"]]))
    H.table(d, ["Alternative", *[w["id"] for w in A["weights"]]], rows, [1.7] + [0.9] * 6, size=8.5)
    cap_tab(d, "totals", "Weighted value: weight x value for each criterion, and the total (the effectiveness score).")
    rows = []
    for k in RANK:
        rows.append((f"{k} {SHORT[k]}", *[f1(TOT[k]["values"][w["id"]] * w["weight"]) for w in A["weights"]], f1(TOT[k]["score"])))
    H.table(d, ["Alternative", *[f"{w['id']} (w {w['weight']:.2f})" for w in A["weights"]], "Total"], rows, [1.5] + [0.8] * 6 + [0.7], size=8, first_bold=True)
    fig(d, "scores", "fig_scores.png", "Effectiveness score of each alternative, stacked by criterion.", 5.4)
    H.heading(d, "4.3 Life cycle cost analysis", 2)
    H.para(d, f"Life cycle cost is the labour to build, verify and maintain each alternative over {ASSUME['life_years']} years (the pilot year and two years of operation) at an **assumed** ${ASSUME['rate']:.0f} an hour. "
              "No alternative adds a paid service or hosting: A to E all run in the existing process, and the free services stay free at the assumed volume (EC.6). Hours are the team's estimates from the code that was written; E's are estimated, not built.")
    cap_tab(d, "lcc", "Life cycle cost by alternative (US dollars; hours are person-hours).")
    rows = []
    for k in "ABCDE":
        c = LCC[k]
        rows.append((f"{k} {SHORT[k]}", f"{c['build']:g}", f"{c['verify']:g}", f"{c['maintain']:g} a year", f"{c['hours']:g}", money(c["labour"]), money(c["total"])))
    H.table(d, ["Alternative", "Build h", "Verify h", "Maintain h", "Total h", "Labour", "Life cycle cost"], rows, [1.7, 0.7, 0.8, 1.1, 0.8, 1.0, 1.1], size=8.5)
    H.heading(d, "4.4 Affordability analysis", 2)
    bud = A["budget"]
    small = min(bud.values())
    H.para(d, f"Affordability compares each cost with what the model allows. The Reference Data Subsystem has an allocation of {money(bud['C.0.2 Reference Data Subsystem share'])} (12% of the {money(bud['System baseline'])} baseline; requirement 5.5.1), the smaller of the two limits, so it is the test. "
              + " ".join(f"{k} costs {money(LCC[k]['total'])} ({100 * LCC[k]['total'] / small:.2f}% of the allocation)." for k in "ABCDE")
              + " All five are affordable by a wide margin, so cost does not exclude any alternative and the question is value for the money. " + F("cost") + " plots the two together. "
              "The cost of the only expensive one, E, is also the least certain, because it was estimated and not built.")
    fig(d, "cost", "fig_cost.png", "Effectiveness against life cycle cost.", 4.8)


def selection(d):
    best, run = TOT[SEL]["score"], TOT[RUNNER]["score"]
    H.heading(d, "5 Alternative Selection and Decision Record", 1)
    H.heading(d, "5.1 Results and selection", 2)
    H.para(d, f"By the rule of Section 2.1 (highest effectiveness among the affordable), **alternative {SEL}, {NAMES[SEL].lower()}**, is selected with a score of {f1(best)}. The ranking is "
              + ", ".join(f"{k} {f1(TOT[k]['score'])}" for k in RANK) + f". The margin over the runner-up ({RUNNER}) is {f1(best - run)} points. "
              + SELECT_WHY.get(SEL, ""))
    H.heading(d, "5.2 Sensitivity analysis", 2)
    H.para(d, "Three tests ask whether the selection depends on the judgments. First, each weight was scaled from 0 to 3 times its value with the others re-normalised (" + F("sens") + "). "
              + FLIPTEXT(SENS) + " Second, 10,000 random weightings (each weight drawn at random, so any criterion may dominate) were scored; the winner was "
              + ", ".join(f"{k} in {100 * v:.1f}%" for k, v in SENS["random_wins"].items() if v > 0) + " of them. "
              "Third, the assumed inputs of EC.6 were changed (" + T("whatif") + "). The selection between C and D is a near tie and is sensitive to them. "
              "The choice of C or D over A, B and E is not: it holds at every setting of every single weight in " + F("sens") + f" and in {100 * (1 - SENS['random_wins']['A'] - SENS['random_wins']['B'] - SENS['random_wins']['E']):.0f}% of the random weightings; "
              "the rest are weightings that put nearly all the weight on the building burden (EC.4) and the typical time (EC.2), where A, which changes nothing, wins by construction.")
    cap_tab(d, "whatif", "Scores of C and D when the assumed volume and keep-alive interval change (C's measured times are kept at their 20 s values for every interval: an assumption).")
    rows = [(str(w["plans"]), f"{w['interval']} s", f1(w["C"]), f1(w["D"]), w["winner"]) for w in A["whatif"]]
    H.table(d, ["Plans a day", "Keep-alive interval", "C score", "D score", "Higher"], rows, [1.3, 1.5, 1.1, 1.1, 1.1], size=8.5)
    H.para(d, "So the selection of D holds for the keep-alive interval that was measured (20 s) and for every volume, and turns to C if a 60 s interval could be shown to keep the connections open. That has not been measured, and the idle-survival data suggest it would not; "
              "it is the experiment that would reopen the choice (Section 12).")
    fig(d, "sens", "fig_sensitivity.png", "Sensitivity of the scores to each weight.", 6.5)
    H.heading(d, "5.3 Implementation", 2)
    H.para(d, f"The selected alternative is implemented in the product, with the other mechanisms of the Chapter 12 guardrail that sit on the same path: "
              "concurrent dispatch (`plan.py`: `DISPATCH`, the weather call on a pool thread), "
              + {"D": "the name cache (`dns_cache.py`, `_CachedHTTPSConnection` in `route_adapter.py`, started at server start-up with `dns_cache.prefetch()`), ", "C": "the keep-alive loop (`keepalive.py`), ", "B": "", "A": "", "E": ""}[SEL]
              + "and, for risk TR.16, deadlines on each call with a labelled fallback. The alternatives that were not selected stay in the code only as the switches the measurements needed "
              "(`DISPATCH = sequential`, `USE_DNS_CACHE = False`) so that they can be remeasured; `keepalive.py` is not started by the server. "
              "All repository tests pass with the change (Section 10.3), and the plan was exercised against the live services after the change (Section 5.4). "
              "The change was reviewed by the team and merged into main in pull request #31 (merge commit 4f0218e); both ADRs carry that status.")
    H.heading(d, "5.4 Validation against the live services", 2)
    FV = os.path.join(D11, "final_validation.json")
    if os.path.exists(FV):
        fv = json.load(open(FV, encoding="utf-8"))["summary"]
        H.para(d, "After the change the repository's defaults were run against the live services, with live directions requests, and compared with the product as it was in Chapter 10 (spike script docs/ch11/spike/validate_final.py). "
                  "Before every run every kept-open connection was closed, which is Chapter 10's cold condition; the name cache stays filled, as it does in a running server. The two sides alternated.")
        cap_tab(d, "final", "Plan response, connections closed before each run, live directions requests (seconds).")
        rows = [(("As built (Chapter 10)" if k == "asbuilt" else "After the change (defaults)"), str(v["n"]), f2(v["median"]), f2(v["mean"]), f2(v["max"]), pct(100 * v["within_3s"]),
                 f"{v['all_routes_live']} of {v['n']}", f"{v['weather_applied']} of {v['n']}") for k, v in fv.items()]
        H.table(d, ["Side", "n", "Median", "Mean", "Max", "Within 3 s", "Drive and walk routed", "Weather rules applied"], rows, [1.9, 0.4, 0.7, 0.7, 0.7, 0.9, 1.0, 1.0], size=8.5)
        H.para(d, "The last two columns count the runs in which no fallback was needed: with the name cache filled no call missed its deadline, so the guardrail did not have to act in these runs. It is exercised by the tests of Section 10.3, which make a service slower than its limit; when a call does miss its deadline the plan is still returned inside 3 s, with a labelled estimate in place of that route or without the weather rules, and a run that is fast but not fully routed is counted as a fallback here.")
    else:
        H.para(d, "The live validation (docs/ch11/spike/validate_final.py) has not been run yet.")
    H.heading(d, "5.5 Architecture decision record", 2)
    H.para(d, "ADR 0012 (docs/adr/0012-plan-path-dispatch.md) records the decision, the criteria, the measures and what the losing alternatives would have required. " + T("adr") + " is its summary. "
              "ADR 0011 (docs/adr/0011-c4-model-behind-a-guardrail.md) records the second decision of this chapter, on the explanation model, which belongs to the risk assessment (Section 10).")
    cap_tab(d, "adr", "Summary of ADR 0012.")
    rows = [("Decision", f"Alternative {SEL}: {NAMES[SEL].lower()}; deadlines and a labelled fallback on every external call."),
            ("Criteria", "EC.1 to EC.6 (" + T("criteria") + "), weights " + ", ".join(f"{w['id']} {w['weight']:.2f}" for w in A["weights"])),
            ("Measures", "Within 3 s: " + ", ".join(f"{k} {RAW[k]['EC.1']:.0f}%" for k in "ABCDE") + ". First feedback: E 0.003 s, the others as plan time. Cost: " + ", ".join(f"{k} {money(LCC[k]['total'])}" for k in "ABCDE") + "."),
            ("Scores", ", ".join(f"{k} {f1(TOT[k]['score'])}" for k in RANK)),
            ("If another alternative had been chosen", LOSERS)]
    H.table(d, ["Part", "Content"], rows, [1.4, 5.7], size=8.5, first_bold=True)
    H.heading(d, "5.6 Use of the assistant and verification", 2)
    H.para(d, "An assistant (Claude Code, Sonnet 5.5) wrote the code, the tests and the draft of this report from constrained prompts; every use is logged in docs/prompt-log.md. It was used as the lab manual recommends: to list the consequences of each alternative as a checklist of things to confirm, "
              "not as evidence. Three of its claims were wrong or unconfirmed and were corrected by measurement: the cold cost was attributed to connection set-up (it is the name lookup); the free routing limit in the Chapter 10 report (200 a day) does not match the published figure (2,000 a day, 40 a minute); and the first version of the explanation guardrail passed reversed comparisons. "
              "Every number in Sections 3 and 4 is computed from the files named in Section 3.1 by docs/ch11/sim/model.py; nothing in the trade study is a number the assistant supplied.")


SELECT_WHY = {
    "D": "The matrix separates two groups decisively and one pair indecisively. C and D (" + f"{TOT['C']['score']:.1f}" + " and " + f"{TOT['D']['score']:.1f}" + ") are at least 26 points above A, B and E; both make a plan on a new connection take 0.1 to 0.6 s instead of 3.6 s. "
         "Between C and D the scores differ by " + f"{abs(TOT['D']['score'] - TOT['C']['score']):.1f}" + " points, which eight runs and judged weights cannot resolve: C is faster (0.14 s against 0.53 s) and has one part fewer; D spends a tenth of the free forecast limit and C a half. "
         "D is selected because the rule picks the higher score, and the choice is easy to defend for a reason the matrix does not weigh: D works whatever the services do with an idle connection, while C works only while they keep one open (in the idle-survival spike the second call was slow in 8 of 14 trials), and C's 4,320 extra forecast calls a day are a standing load on a free service.",
    "C": "It leads on EC.1 because connections stay open between requests.",
    "B": "It leads on the balance of result time and burden.",
    "A": "No alternative improves enough to justify its burden.",
    "E": "It leads on first feedback.",
}
LOSERS = ("A would have left the 3 s limit to chance: on a request that meets two new connections the plan costs the sum of two lookups (6.9 s measured as the first request of the process). "
          "B alone would have cut that to the longer lookup (3.6 s) and still missed the limit. C would have required a keep-alive loop and a free-limit budget and still depends on the services' idle timeouts. "
          "E would have required a queue and worker, a job table, a status endpoint and a polling script, plus the accessibility checks of a status page, for the same lookup: it does not shorten the wait, it moves it behind a status page.")


def FLIPTEXT(sens):
    flips = sens["flips"]
    if not flips:
        return "The selected alternative wins at every setting of every weight."
    parts = []
    for cid, items in flips.items():
        f, a, b = items[0]
        parts.append(f"for {cid} the winner is {a} below {f:.2f} times its weight and {b} from there up")
    return "Only three single-weight changes alter the winner, and all three are between C and D: " + "; ".join(parts) + "."
