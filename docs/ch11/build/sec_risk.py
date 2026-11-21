"""Sections 6 to 10 of the report: risk identification, matrix, top-risk plan, monitoring, register and guardrails."""
from docx.shared import Pt, RGBColor

import docx_helpers as H
from report_lib import A, F, NAMES, SEL, T, TESTS, cap_fig, cap_tab, f1, f2, fig, money, pct  # noqa: F401

RISK = {r["id"]: r for r in A["register"]}
TOP = A["risks"][0]
MECH = {"A": "no further mechanism", "B": "no further mechanism", "C": "a keep-alive loop that holds one connection to each service open",
        "D": "a name cache that removes the host-name lookup from every new connection", "E": "a queue with polling"}[SEL]


def risk_ident(d):
    H.heading(d, "6 Risk Identification and Risk Table", 1)
    H.heading(d, "6.1 How the risks were found", 2)
    H.para(d, "The risks were derived from the architecture model, not brainstormed. The first-level IDEF0 of Chapters 6 and 7 has 22 input/outputs "
              "(IO.1 to IO.22) between the eight subsystems and the external systems, and the Chapter 10 sequence diagram shows them in order. "
              "Each interaction was read against the eleven questions of the lab manual: is it correct but misunderstood, degraded, of the wrong type, "
              "intercepted, too early or late, in shortage or excess, in conflict, under extreme conditions, absent, dependent on an earlier interaction "
              "that failed, or technology-dependent. Most pairs of interaction and question give nothing; "
              + T("inspect") + " lists the ones that gave a risk, in the order they were met (outer interactions first, then the first level).")
    cap_tab(d, "inspect", "Interactions of the architecture model inspected and the unwanted behavior each question produced.")
    rows = [
        ("IO.4 Weather Request, IO.5 Weather Forecast Data (F.2.2 and X.3); route request and answer (C.0.2 and X.6)", "Too late; does not take place; technology-dependent",
         "The forecast or the route answers after the display limit, or not at all. Measured: a new connection waits about 3 s for a host-name lookup on the development laptop.", "TR.16"),
        ("Route request and answer (C.0.2 and X.6)", "In shortage",
         "The free routing plan refuses requests when its limit is reached; the plan falls back to labelled straight-line estimates.", "TR.11"),
        ("IO.6 Reviewed Emission Factors, IO.14 Emission Factor Record (X.4, F.2.2)", "Correct but misunderstood or misused",
         "A tailpipe-only factor is read as a full life-cycle figure, or a placeholder factor (scooter, carpool) is read as reviewed.", "TR.1"),
        ("IO.20 Alternative Recommendation, IO.3 Commute Result and Advice (F.2.5 to F.2.6)", "Wrong type of input; technology-dependent",
         "If a language model words the explanation, the text can be well formed and wrong: a reversed comparison, an invented figure.", "TR.4"),
        ("IO.1 Commuter Entries and Requests, IO.19 Trip Record Extract (F.2.1, F.2.4)", "In excess; intercepted",
         "Start and destination labels are kept finer than the coarse location the requirements allow, and are readable if the store is copied.", "TR.10"),
        ("IO.15 Trip Weather Forecast to F.2.5", "Dependent on an earlier interaction that did not take place correctly",
         "With no forecast the weather rules are not applied, so a walk or ride is recommended in rain the system never saw.", "TR.16"),
        ("IO.11 Hosting Service Status, IO.22 Service Status Record (X.5, F.2.0)", "Under extreme conditions; does not take place",
         "The host is down or slow at a busy time; the 99.5 percent availability is unproven.", "TR.7 (register)"),
    ]
    H.table(d, ["Interaction inspected", "Question that fired", "Unwanted behavior found", "Risk"], rows, [2.2, 1.4, 2.7, 0.8], size=8)
    H.para(d, "Three kinds of risk go to the product register (Section 10) and not to the system-level table: those that apply to one component and not to the system, "
              "those that belong to building with an assistant (they are not interactions of the model), and those the question list did not reach "
              "but earlier chapters had already recorded (TR.13 to TR.15). Five risks are system-level in the sense of the assignment: each crosses a "
              "subsystem boundary of the model and touches a requirement of the whole system. They are in the risk table below.")

    H.heading(d, "6.2 Risk table", 2)
    H.para(d, "The table has the columns the assignment names. The description states the unwanted behavior, what is affected, the type of risk and the "
              "life cycle phase. Likelihood and the three impacts use the 1 to 5 scales of " + T("scales") + "; the overall impact and the overall risk level are "
              "calculated as set out in Section 6.4. The ratings are the team's engineering judgments, made from the measurements named in the description, "
              "and are stated as of 22 November 2026 with the controls that exist at that date.")
    desc = {
        "TR.16": "**Unwanted behavior:** a plan meets a new connection and waits about 3 s for a host-name lookup before the forecast or route call even starts (the development laptop's resolver, 21 of 24 measured trials), so the result page misses the 3-second limit (3.4.2.1) and the forecast misses its 1.0 s limit (5.4.4). **Affected:** the commuter's result and the weather rules of the recommendation (F.2.2, F.2.5, F.2.6; X.3, X.6). **Type:** performance and availability. **Phase:** design and test (where it is prevented), operations (where it occurs).",
        "TR.11": "**Unwanted behavior:** the routing service refuses requests at its free limit or changes its host; the plan falls back to straight-line estimates, so distances and times are less accurate, and the Chapter 11 measurements were stopped by a refusal. **Affected:** every route-based row of the comparison (F.2.2, F.2.5; X.6). **Type:** availability and cost. **Phase:** operations (pilot).",
        "TR.4": "**Unwanted behavior:** an explanation worded by a language model is well formed and wrong: in 20 of 40 recorded cases a small local model reversed a comparison or called a slower option the fastest. **Affected:** the commuter's trust and the overclaiming rule (2.1.10, need 1.4.3) at F.2.6 and the C.4 explanation model. **Type:** technical (correctness, trust). **Phase:** design and operations.",
        "TR.10": "**Unwanted behavior:** confirmed trips keep their start and destination labels, finer than the coarse location the requirements allow, so a copied store reveals a person's routine. **Affected:** the commuter and the pilot sponsor (F.2.1, F.2.4; IO.1, IO.19). **Type:** security and privacy. **Phase:** design and operations.",
        "TR.1": "**Unwanted behavior:** a reviewed factor is applied outside its scope (tailpipe only; scooter and carpool use labelled placeholders), so an estimate looks firmer than it is. **Affected:** the CO2e estimate and the baseline difference (F.2.2, F.2.3; IO.6, IO.14). **Type:** technical (data validity). **Phase:** design and operations.",
    }
    cap_tab(d, "risktable", "Risk table: five system-level risks, highest level first (scales and calculation in Sections 6.3 and 6.4).")
    rows = []
    for r in A["risks"]:
        rows.append((f"{r['id']} {r['short']}\n{desc[r['id']]}", str(r["L"]), str(r["cost"]), str(r["sched"]), str(r["tech"]), f2(r["overall"]),
                     f"{r['level']:.2f} {r['band']}"))
    H.table(d, ["Description", "Likeli-hood", "Impact cost", "Impact schedule", "Impact technical", "Overall impact", "Overall risk level"], rows,
            [3.2, 0.6, 0.55, 0.7, 0.7, 0.6, 0.75], size=8)

    H.heading(d, "6.3 Rating scales", 2)
    cap_tab(d, "scales", "Meaning of 1 to 5 for likelihood and for each impact.")
    rows = [
        ("1", "Rare: not expected in the pilot", "No requirement affected", "No delay", "Less than $500"),
        ("2", "Unlikely: could happen once", "A requirement degraded for a minority of uses, with a labelled fallback", "Under 1 day", "$500 to $2,000"),
        ("3", "Possible: expected a few times", "A requirement missed in part of the pilot", "1 to 3 days", "$2,000 to $10,000"),
        ("4", "Likely: expected most weeks", "A shall requirement not met, or a wrong statement shown to a commuter", "3 to 7 days", "$10,000 to $50,000"),
        ("5", "Almost certain: already observed or expected every day", "The core value proposition fails, or personal data is exposed", "More than 7 days, or the pilot window is missed", "Over $50,000"),
    ]
    H.table(d, ["Rating", "Likelihood", "Technical impact", "Schedule impact (pilot results due 18 Dec 2026)", "Cost impact (baseline $750,000)"], rows,
            [0.5, 1.6, 2.1, 1.5, 1.2], size=8)

    H.heading(d, "6.4 How the overall impact and the risk level are calculated", 2)
    top = TOP
    H.para(d, "**Overall impact** is the weighted mean of the three impacts: 0.5 x technical + 0.25 x schedule + 0.25 x cost. Technical counts double because the sponsor's measures "
              "of effectiveness are mostly about whether the product works (3.4.2.1, 2.1.10, 3.4.4.1), while schedule and cost each have one requirement (3.4.1.2, 3.4.1.1). "
              "**Overall risk level** is likelihood x overall impact, a number from 1 to 25. The bands are High for 12 or more (red), Medium from 6 to under 12 (yellow) and Low under 6 (green). "
              f"Worked example, {top['id']}: overall impact = 0.5 x {top['tech']} + 0.25 x {top['sched']} + 0.25 x {top['cost']} = {f2(top['overall'])}; "
              f"risk level = {top['L']} x {f2(top['overall'])} = {top['level']:.2f}, High. On the matrix the impact axis uses the overall impact rounded to the nearest whole number "
              "(half rounds up), which keeps every cell's colour equal to the band of the exact level for the risks of this table.")


def risk_matrix(d):
    H.heading(d, "7 Risk Matrix", 1)
    H.para(d, "The five risks are plotted on the 5 x 5 matrix of " + F("matrix") + ". Likelihood runs from 1 at the bottom to 5 at the top and overall impact from 1 at the left to 5 at the right, "
              "so the axes are the likelihood and the overall impact of the risk table. A cell is green when likelihood x impact is under 6, yellow from 6 to 11 and red from 12; "
              "the colours are the team's tolerance for the pilot and another customer might set them differently.")
    cells = {}
    for r in A["risks"]:
        cells.setdefault((r["L"], r["overall_cell"]), []).append(r["id"])
    placed = "; ".join(f"{', '.join(v)} in the cell likelihood {k[0]}, impact {k[1]}" for k, v in cells.items())
    import os
    from report_lib import SHOT
    own = os.path.exists(os.path.join(SHOT, "risk_matrix.png"))
    fig(d, "matrix", "fig_risk_matrix.png", "Risk matrix of the five system-level risks: the Innoslate Risk Diagram of model 11.5." if own else "Risk matrix of the five system-level risks (drawn from the risk table; the Innoslate view of model 11.5 shows the same cells).", 5.0, shot="risk_matrix.png")
    if own:
        H.para(d, "In the Innoslate view the likelihood rows are named Low, Medium Low, Medium, Medium High and High (1 to 5 in the table) and the impact columns Negligible, Minor, Moderate, Serious and Critical (1 to 5). "
                  "The colours are Innoslate's default scheme. It gives each of the five risks the same colour as the thresholds above; the schemes differ only in a few cells where none of these five sits "
                  "(for example likelihood 2, impact 3, where TR.19 and TR.14 of the register are: yellow by the thresholds, green in Innoslate).")
    H.para(d, f"Reading the matrix: {placed}. {TOP['id']} is the only risk in the red region. TR.11 is the highest of the yellow ones and the only one with likelihood 5 "
              f"(the refusal happened during the measurements of this chapter), but its consequence is held at 2 because a labelled estimate is already the fallback. "
              "TR.4, TR.10 and TR.1 are lower because the explanation model is off by default, the cache keeps no account, and the factors are reviewed. "
              "The matrix is therefore consistent with the table: the red risk is the one that is both likely and able to break a shall requirement without a fallback.")


def top_risk(d):
    top = TOP
    d.add_page_break()   # the top risk is on a page of its own, as the slide of the assignment
    H.heading(d, "8 Top Risk and Mitigation Plan", 1)
    H.para(d, f"**Selection.** {top['id']} has the highest level in the table ({top['level']:.2f}; the next is {A['risks'][1]['id']} at {A['risks'][1]['level']:.2f}) and is the only risk in the red region "
              "of the matrix. It is also the risk to the product's core promise, immediate feedback (need 1.1.1; requirement 2.1.2).")
    # slide-like page
    t = d.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    H.shade(c, "EEF3F9")
    H.set_cell(c, f"TOP RISK {top['id']}: {top['short']}\n"
                  "**What happens:** a commuter submits a trip and the page does not return for 3 to 7 s, because the first step of a new connection to the forecast or route service is a host-name lookup that took about 3.07 s in 21 of 24 trials on the development laptop. The forecast then misses its 1.0 s limit.\n"
                  f"**Why it is the top risk:** likelihood {top['L']} (observed in Chapter 10: 8.3% of cold plans within 3 s; reproduced in Chapter 11), impact technical {top['tech']} (a shall requirement, 3.4.2.1), schedule {top['sched']}, cost {top['cost']}; level {top['level']:.2f}, High.\n"
                  "**Strategy: MITIGATE.** It cannot be eliminated (the services are external and free) and should not be accepted or deferred (it breaks a shall requirement before the pilot).\n"
                  f"**Plan:** (1) run the two calls side by side; (2) {MECH}; (3) enforce a deadline on each call (forecast 1.0 s, routes 1.2 s) and show a labelled estimate when one is missed; (4) measure on the deployed host with at least 30 cold runs before the pilot; (5) track the counters at every review point.\n"
                  "**Done when:** 95% of plans on the deployed host return within 3 s, with every plan that used a fallback saying so.",
               size=13)
    for para in c.paragraphs:
        para.paragraph_format.space_after = Pt(9)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    d.add_page_break()
    H.para(d, "**Why mitigate.** The assignment offers four strategies. Eliminating the risk would mean removing the external services, which are the product's source of routes and weather. "
              "Accepting it would leave a shall requirement unmet in the normal case between commuters. Deferring it would push the work past the first measurements of the pilot, which are due before 18 December 2026. "
              "The failure can be reduced in three independent ways (parallel calls, no waiting for the name lookup, a deadline) and contained in a fourth (a labelled fallback), all inside the team's own code.")
    cap_tab(d, "plan", "Mitigation plan for the top risk: actions, the model entity each one acts on, and status on 22 November 2026.")
    rows = [
        ("1 Run the forecast call beside the route calls", "F.2.2.3 Request Weather Forecast, F.2.2.4 Resolve Trip Forecast; C.0.2; requirement 5.5.3", "Built: `DISPATCH = concurrent` in `plan.py`; test `test_concurrent_dispatch_costs_the_longer_call_not_the_sum`"),
        (f"2 {MECH[0].upper() + MECH[1:]}", f"C.0.2 and X.3, X.6; alternative AL.{SEL}; IO.4, IO.5", "Built: " + {"D": "`dns_cache.py` and `_CachedHTTPSConnection`; `tests/test_dns_cache.py`", "C": "`keepalive.py`", "B": "(none)", "A": "(none)", "E": "(not built)"}[SEL]),
        ("3 Deadline on each call, fallback when missed", "IO.24 Forecast Query Context (1.0 s); requirements 5.4.4, 5.5.3, 3.4.2.1; C.0.2.3, C.0.2.4", "Built: `WEATHER_DEADLINE_S`, `ROUTE_DEADLINE_S`; `tests/test_dispatch_guardrail.py` (failure path)"),
        ("4 Label every fallback", "Recommendation weather note; route `source`; requirement 2.4.4 (method disclosure)", "Built: the plan says weather rules were not applied; each estimated route says why"),
        ("5 Measure on the deployed host, 30 or more cold runs", "Chapter 10 decision D9; X.5 Hosting Provider; requirement 3.4.2.1", "Open: no deployed host yet; owner Technical Architecture Lead"),
        ("6 Track the counters at every review point", "Risk TR.16 in model 11.5; `plan.dispatch_stats()`", "Built (counters); review points in Section 9"),
    ]
    H.table(d, ["Action", "Model entities it acts on", "Status and evidence"], rows, [2.2, 2.5, 2.4], size=8.5)


def monitoring(d):
    H.heading(d, "9 Risk Monitoring and Control", 1)
    H.para(d, "Monitoring starts now, in development and test, not when the service is operating. The aim is to see the likelihood and the impact of TR.16 change before a commuter does.")
    cap_tab(d, "monitor", "Indicators, thresholds and review points for the top risk, in the order of the life cycle.")
    rows = [
        ("Design and build (now)", "Plan response in the harness, cold condition, 95th percentile (docs/ch10/instrument and docs/ch11/spike)", "Under 3 s; any run over 3 s with no fallback is a defect", "Each merge that touches `plan.py` or `route_adapter.py`", "Developer"),
        ("Test (before the pilot)", "Share of cold runs within 3 s on the deployed host (30 or more runs)", "At least 95%", "Stage gate: pilot readiness", "Technical Architecture Lead"),
        ("Test (before the pilot)", "Name-lookup time per new connection (the phase spike)", "Under 0.2 s after the cache is filled; over 1 s means the cache is not used", "Same gate; repeat on any change of host or network", "Technical Architecture Lead"),
        ("Pilot start", "`weather_missed_deadline` over `plans` (counters of `plan.dispatch_stats()`)", "Under 5% of plans; over 10% raises the likelihood to 5", "Weekly during the pilot", "Quality, Risk and Documentation Lead"),
        ("Pilot start", "Routes served as estimates over routes asked (per-mode fallback count) and refusals from the routing service", "Under 10%; any refusal opens TR.11", "Weekly", "Quality, Risk and Documentation Lead"),
        ("Pilot start", "Free-service use: Open-Meteo calls a day against 10,000", "Under 50%", "Weekly", "Project Manager"),
    ]
    H.table(d, ["Phase", "Indicator", "Threshold", "Review point", "Owner (role)"], rows, [1.0, 2.5, 1.7, 1.2, 0.9], size=8)
    H.para(d, "**Control.** At each review point the owner re-rates likelihood and the three impacts of TR.16 against the thresholds and records the change in the risk entity. "
              "If likelihood stays at 4 or higher after the deployed-host measurement, the handling changes from mitigate to a change of the requirement: ask the sponsor to move 3.4.2.1 to a stated percentile or to approve a paid, closer service. "
              "If it falls to 2, the risk is kept open for one more review and then closed.")
    H.para(d, "**What the modeling tool does.** The risk is an entity in the Innoslate model (TR.16 in model 11.5) with Probability, Consequence and Status attributes, so the risk matrix view updates when the "
              "ratings are edited. It is related to the functions it comes from (F.2.2.3, F.2.2.4), the input/output IO.5, the requirements it threatens (3.4.2.1, 5.4.4, 5.5.3) and, through the decision, to the alternative that was built (AL." + SEL + "). "
              "Following those relations answers two questions the table cannot: which requirements are exposed if the risk occurs (the three above), and which risks are exposed if a function or a component changes "
              "(open F.2.2.4 and its relations list TR.16 and TR.4). The test evidence is held as the name of each test in the plan table, so a review can open the test that exercises the failure path. "
              "When a later chapter changes a function, the relations make the affected risks the first thing to re-rate.")


def register(d):
    H.heading(d, "10 Product Risk Register and Guardrails", 1)
    H.para(d, "The register is `docs/risks.md` in the repository, built from the same ratings as the risk table so that the two cannot disagree. It has 15 risks: the five of the table (one of them, TR.4, is AI-specific), six more that are specific to an "
              "AI-enabled product or to building with an assistant (all seven are marked AI), and four earlier ones (TR.13 to TR.15 and TR.7) that the model already held. "
              "Every row has a model cross-reference, a control and the test that exercises it. The ratings are the team's judgments; none was generated.")
    cap_tab(d, "register", "Product risk register (rows in order of level). AI marks the risks specific to an AI-enabled product.")
    rows = []
    for r in A["register"]:
        rows.append((r["id"], r["short"], "AI" if r["ai"] else "", str(r["L"]), f2(r["overall"]), f"{r['level']:.2f} {r['band']}"))
    H.table(d, ["ID", "Risk", "AI", "L", "Overall impact", "Level"], rows, [0.55, 4.1, 0.35, 0.35, 0.9, 0.95], size=8)
    fig(d, "regmatrix", "fig_register_matrix.png", "All 15 register risks on the same matrix.", 4.6)
    H.heading(d, "10.1 The AI-specific risks and what stops each", 2)
    cap_tab(d, "ai", "AI-specific risks, the control built, and the test that tries to get past it.")
    rows = [
        ("TR.4 Well-formed but wrong output", "Guardrail: the model may only rephrase; its text is checked against the calculated values; otherwise the template is shown (fallback)", "`test_a_reversed_comparison_is_rejected` and eleven more rejection tests"),
        ("TR.17 Model unavailable or slow", "Fallback: 2.0 s timeout, template text, 60 s circuit breaker", "`test_an_unavailable_model_falls_back_and_the_breaker_stops_asking`"),
        ("TR.18 Untrusted input reaches the prompt", "Guardrail by construction: the prompt is the template sentence only", "`test_untrusted_text_never_reaches_the_prompt` (a route source carrying 'IGNORE ALL PREVIOUS INSTRUCTIONS')"),
        ("TR.19 Data leaves the machine", "Guardrail: a model host that is not loopback is refused", "`test_a_model_on_another_machine_is_refused_so_trip_facts_do_not_leave`"),
        ("TR.20 Response schema drift", "Guardrail: a reply without a text `response`, not JSON, or not text is treated as unavailable", "`test_a_reply_without_a_response_field_is_schema_drift`"),
        ("TR.21 Dependency abandoned", "The model is optional and off by default; versions are pinned; licence checked (Apache 2.0)", "None: a review item at each gate"),
        ("TR.22 Assistant-written code wrong", "Prompt log; tests from the requirement text; review before merge. The first version of the guardrail passed reversed comparisons; reading the outputs found them", "Whole suite; the recorded outputs are the regression corpus"),
    ]
    H.table(d, ["Risk", "Control (guardrail prevents; fallback contains)", "Test of the failure path"], rows, [1.7, 3.1, 2.3], size=8)
    H.heading(d, "10.2 Evidence for the top AI risk: the spike on the explanation model", 2)
    import json, os
    from report_lib import D11
    sp = json.load(open(os.path.join(D11, "spike_gpu.json"), encoding="utf-8"))
    v1 = json.load(open(os.path.join(D11, "spike_gpu_guard_v1.json"), encoding="utf-8"))
    b = sp["B"]
    H.para(d, f"The explanation model (C.4) is a template today. To rate TR.4 from evidence instead of opinion, 40 explanation cases were given to a locally hosted model (qwen2.5:1.5b under Ollama 0.40.17, on the laptop's GPU) with the instruction to rephrase the template sentence, "
              f"and every raw reply was checked against the calculated values (docs/ch11/spike/measure_c4.py). The first version of the check rejected {v1['B']['raw_unsupported_count']} of 40; it missed a whole class of error, comparisons that are reversed (a ride 10 minutes longer than the fastest described as 10 minutes faster), "
              f"which was found by reading the recorded outputs and not by the assistant. With the direction rules added, {b['raw_unsupported_count']} of 40 ({100 * b['raw_unsupported_rate']:.1f}%) were rejected and none reached the page (" + F("c4") + "). "
              f"The model answered in a median of {b['latency_ms_median'] / 1000:.2f} s (95th percentile {b['latency_ms_p95'] / 1000:.2f} s) with the model already loaded; the first call after the server started took up to 44.7 s. "
              f"It also read at a higher grade than the template (Flesch-Kincaid {b['fk_grade_mean_raw']:.1f} against {sp['A']['fk_grade_mean']:.1f}), so on this evidence it adds variety of phrasing and nothing the requirement asks for. "
              "That is why the model is off by default, why the template stays authoritative, and why TR.4 is rated 3 and not 5. The recorded wrong outputs are the corpus the tests use to try to defeat the guardrail, which is the use of the assistant that the lab manual recommends for this increment; "
              "the assistant was not asked to rate any risk.")
    fig(d, "c4", "fig_c4.png", "Explanation model spike: share of 40 raw outputs rejected by each version of the check, and the reasons.", 6.0)
    H.heading(d, "10.3 What was built for the top risk, and why", 2)
    H.para(d, f"For {TOP['id']} we built a **guardrail and a fallback**. The guardrail prevents the failure: a call that has not answered by its deadline (forecast 1.0 s, routes 1.2 s) is dropped, so the plan returns inside the 3-second display time "
              "whatever the service does. The fallback contains what the guardrail cannot prevent: the commuter still gets a recommendation, labelled with what was not applied (weather rules) or which numbers are estimates (routes). "
              "A late call is left to finish on its own thread, so that its connection returns to the pool and the next request finds it open. "
              "We chose a guardrail first because the failure is a missed limit, not a wrong value, so it can be prevented by construction; we added the fallback because prevention costs accuracy when it triggers.")
    cap_tab(d, "tests", "Tests of the failure path for the top risk (tests/test_dispatch_guardrail.py and tests/test_dns_cache.py).")
    rows = [
        ("test_a_slow_forecast_does_not_hold_the_plan_and_is_labelled", "The forecast would take 3 s; the plan returns in under 1.6 s with 'Weather was not available...' and still recommends a mode (both dispatches)"),
        ("test_a_slow_route_service_gets_labelled_estimates_inside_the_deadline", "Three routes hang for 3 s; the plan gets three labelled estimates in under 1 s; the late 9.9 km answer is not used and nothing is cached"),
        ("test_one_slow_mode_falls_back_alone", "Only the bike route is slow; drive and walk stay routed, bike is an estimate"),
        ("test_a_failing_forecast_call_is_also_handled", "The forecast call raises a network error; the plan still returns"),
        ("test_the_monitoring_counters_record_a_missed_deadline", "The indicator of Section 9 counts the miss"),
        ("test_a_connect_to_a_bad_cached_address_forgets_it_and_falls_back", "A stale cached address does not break a request"),
        ("test_the_certificate_is_still_checked_for_the_host_name", "The cache changes the address, never who is trusted"),
        ("test_a_failing_tick_never_raises", "A keep-alive failure cannot reach a commuter"),
    ]
    H.table(d, ["Test", "What it tries and what must happen"], rows, [3.3, 3.8], size=8)
    H.para(d, f"All {TESTS['tests']} tests of the repository pass, including these 54 new ones (the 420 that existed are unchanged).")
