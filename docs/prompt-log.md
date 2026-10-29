# GenAI prompt / provenance log

Rule: every GenAI-assisted change is logged here with the tool, the (constrained) prompt, the source text it was constrained by, what it produced, and the human review. Do not use a broad prompt to generate the whole project.

## Entry 001 - 2026-10-05 - Repository restructure and UC.1 walking skeleton

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen (team member) |
| Branch | `feat/walking-skeleton-uc1` |
| Prompt (summary of the user's request, originally written in Chinese) | Fix the two weakest Milestone 1 rows (Walking Skeleton, Model-to-Product Linkage): restructure the repo per BMA Section 7.9 (README with OpsCon, docs/context.md, SPEC.md, prompt log) and build one stubbed end-to-end UC.1 path; choose the stack that is easiest for a Python-leaning team. |
| Constraining sources given to the assistant | BMA Sections 4.3, 7.1, 7.3, 7.7, 7.9; Stakeholder Needs and Requirements report Tables 10-12 (SRD); Innoslate export `EcoCommute 10.4.xml` (original source export at that time; superseded by 10.5 and 10.6) (requirement `satisfies` relationships); Milestone 1 criteria PDF |
| What the assistant produced | `README.md` (OpsCon copied verbatim from BMA 7.1), `docs/context.md`, `docs/walking-skeleton.md`, `docs/traceability.md`, `docs/environment.md`, `docs/adr/0001-initial-toolchain.md`, `SPEC.md` (generated from the SRD tables by script), `src/` participants C.1-C.4, X.1 simulation, X.3 stub, `src/model_trace.py`, `tests/`; removed the generic `math_utils` starter files and old `src/main.py` |
| Constraints applied | Stub boundaries per BMA 7.9 (hard-coded explanation, no real source access, live model calls, retries, exception handling or runtime logging); code and tests tagged with UC.1 action IDs and SRD IDs; placeholder emission factors labelled as not reviewed |
| Not generated / not claimed | Reviewed emission factors; a working local language model; a web UI; off-nominal behavior |
| Human review | **Pending.** Reviewer name and date: ____________ . Checklist: (1) OpsCon in README matches BMA 7.1; (2) context.md matches BMA 4.3; (3) SPEC statements match the SRD; (4) call order matches the Sequence Diagram; (5) `python -m src.main` and tests pass on a second machine. |

## Entry 002 - 2026-10-05 - C.4 explanation need/requirement, model 10.6

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/c4-explanation-requirement` |
| Prompt (summary, originally Chinese) | Add one requirement for C.4 and give an updated Innoslate XML; update the Canvas submission. |
| Constraining sources | Entry 001 outputs; Innoslate export `EcoCommute 10.5_C1-C4`; SND/SRD wording conventions (need: "I need ... so that ..."; requirement: one "shall", measurable MOE, validation, method); BMA 7.9 (C.4 may only explain a calculated result) and risk R8 |
| What it produced | Need 1.1.8 and requirement 2.1.10 with trace/satisfy/perform links in `docs/model/EcoCommute_10.6_C4-explanation-req.xml` (script-patched XML, 2 entities and 12 relationships added, nothing removed); `explain_result()` now takes only calculated values; new test; regenerated SPEC.md (28 requirements); doc updates |
| Not claimed | The Stakeholder Needs report (docx/pdf) is not updated: it still says 20 needs and 27 requirements |
| Human review | **Pending.** Reviewer and date: ____________ . Check the requirement wording and the XML import (10.5 import verified by screenshot; 10.6 import pending). |

## Entry 003 - 2026-10-05 - Fixes after an external review of the Canvas submission

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `fix/model-status-and-2-1-10-test` |
| Prompt (summary, originally Chinese) | Evaluate a second reviewer's comments on the submission; adopt the reasonable ones. |
| Constraining sources | Reviewer comments; Innoslate Intelligence screenshot of the imported 10.5 (C.1-C.4) model; Entry 002 outputs |
| What it produced | `explain_result()` now also takes the estimated difference, factor source and version, so the explanation states every fact named in requirement 2.1.10; new test `test_explanation_contains_required_facts`; `tests/test_model_linkage.py` now reads the UC.1 actions from the exported XML instead of a hard-coded list; docs wording corrected (import status, what the linkage test checks); screenshot saved as `docs/model/intelligence-10.5-c1-c4.webp`; `.gitignore` excludes the Canvas submission files |
| Not claimed | 10.6 has not been imported into Innoslate or run through Intelligence |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 004 - 2026-10-06 - Record the Innoslate import of model 10.6

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `docs/model-10-6-verified` |
| Prompt (summary, originally Chinese) | The team imported 10.6 into Innoslate; here is the Intelligence screenshot; record it. |
| Constraining sources | Team screenshot of the Innoslate Intelligence dashboard (116 entities, 34 requirements, no errors, 81% pass rate) |
| What it produced | `docs/model/intelligence-10.6.webp`; import status updated in `docs/context.md` and `docs/traceability.md` (O-7 closed) |
| Not claimed | Diagrams still show C.0 only until they are redrawn; no human has yet reviewed the 10.6 requirement wording |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 005 - 2026-10-18 - Chapter 4 and 5: first-level IDEF0, system requirements, report section

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `docs/ch4-ch5-system-requirements` |
| Prompt (summary, originally Chinese and English) | Complete the Chapter 4 and 5 assignment from the Innoslate model and the System Requirements Definition rubric: Metafunction, IDEF0-A0, first-level IDEF0, system requirements with rationale, MOP/MOS, verification, risks, and a Word report; then fix the Innoslate import and Intelligence errors. |
| Constraining sources | Lab manual v3.0 (Chapters 4, 5, 7), the model `EcoCommute 10.5 c1-c4 ver.xml`, SPEC.md and the SRD (requirement values), the airport-kiosk example XML (structure of generated requirements), team screenshots of the imported model |
| What the assistant produced | `docs/model/EcoCommute_10.7_C4-C5_system_requirements.xml` (adds Metafunction F.1-F.6, first-level F.2.0-F.2.7, IO.1-IO.22, requirement group 3 with 39 requirements, 9 technical risks, SysRD artifact; script-built, existing entities unchanged apart from conduit descriptions); `docs/ch4-ch5/` report (.docx), diagrams, and `patch_fix.py` (the script the assistant ran on the generated XML to renumber Operate Service to F.2.0 and add satisfies links; its output is the committed XML, the team did not run it and re-imported the XML instead) |
| Not generated / not claimed | The Generate Requirements script was not run (statements follow its pattern); the 3 s display time and minimum group size 5 are SRD proposals; first-level mechanisms are not allocated yet (next chapter); team contributions are a draft from README roles |
| Human review | Team accepted the contribution table and the proposed values. Intelligence on the re-imported 10.7 model (the committed XML already contains the patch): 81% pass, no errors, warnings only (`docs/ch4-ch5/diagrams/innoslate_intelligence.png`). Reviewer and date: ____________ . |

## Entry 006 - 2026-10-18 - Final Chapter 4 and 5 report for Canvas

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5; final wording and layout edit with Codex (per the output location of the edited file; confirm) |
| Requested by | Luyu Chen |
| Branch | `docs/ch4-ch5-v5-readable-diagrams` |
| Prompt (summary, originally Chinese) | Replace the report figures with the team's own Innoslate screenshots (requirements diagram in four parts, traceability matrix, spider diagrams); then review the edited final report for Canvas and sync the repository. |
| Constraining sources | The Innoslate model 10.7 as imported by the team; the team's screenshots; the System Requirements Definition rubric |
| What it produced | `docs/ch4-ch5/EcoCommute_Team6_Ch4-Ch5_System_Requirements_Definition_Final.docx` (replaces the draft v5); `docs/ch4-ch5/diagrams/` (Innoslate screenshots); pointers to the 10.7 export in `docs/context.md` and `docs/traceability.md`; open item O-8 |
| Changes made by the team in the final edit | The 3 s display time and minimum group size 5 are marked TBD pending sponsor approval (assumptions, considerations and the two requirement rows); figures re-laid out for portrait pages; contribution table confirmed |
| Not claimed | The sponsor has not confirmed the TBD values; first-level mechanisms are still unallocated |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 007 - 2026-10-25 - Chapter 6 and 7 report: trace, first-level function architecture, N2, hierarchy

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `docs/ch6-ch7-function-architecture` |
| Prompt (summary, originally Chinese) | Complete the Architecture Definition: Function assignment (Chapter 6 tracing plus Chapter 7 first-level function architecture) from the repository, the new Innoslate export and the lab manual, and satisfy the rubric and the TA's guidance (hierarchy, N2, traceability with functions in the rows, every figure explained once). |
| Constraining sources | Innoslate export EcoCommute_10.7 of 2026-10-24 (copy in `docs/model/`); Lab Manual v3.0 sections 6.1-6.3 and 7.1-7.3; the Architecture Definition: Function rubric |
| What it produced | `docs/ch6-ch7/EcoCommute_Team6_Ch6-Ch7_Architecture_Definition_Function.docx` and `.pdf`; `docs/ch6-ch7/diagrams/` (Innoslate screenshots with traced lines added by `docs/ch6-ch7/scripts/`; only the sequence diagram is drawn from the model data); `docs/model/EcoCommute_10.8_C6-C7_trace_update.xml` (10.7 plus two relationship edits found by the trace: IO.3 also generated by F.2.1, IO.12 also received by F.2.4; generated by script; the team reports importing it into Innoslate afterwards; also restores 42 relationships the 2026-10-24 export had lost: risk-to-requirement `related to` links and F.0 traced to requirement 3) |
| Findings the trace produced | Entry Form had no IDEF0 output; F.2.4 received no trip details; internal flows are not on the action diagram (kept in the sequence diagram) |
| Not claimed | UC.2 and the operations actions are not traced; the sequence diagram (Figure 11) is drawn from the model data, not an Innoslate view; the import result of the 10.8 XML is the team's report and is not recorded here; the contribution table was drafted from the team roles and then confirmed by the team |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 008 - 2026-10-27 - Minimal Flask web entry for C.1

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Start the first modification step: on a new branch, add a minimal web entry without changing the existing logic; use Flask if it is better. |
| Constraining sources | Existing C.1-C.4 code and `docs/adr/0001-initial-toolchain.md` (which requires a new ADR for a web layer) |
| What it produced | `src/c1_web_front_end/web_app.py` and `templates/commute.html` (form, validation, result page); `src/main_web.py`; `tests/test_web_app.py` (5 tests, skipped without Flask); `docs/adr/0002-flask-web-entry.md`; Flask added to `requirements.txt`; README run instructions |
| Not claimed | C.2-C.4 are unchanged, so factors, weather and storage are still stubs; the known cumulative-difference issue in C.3 `update_trends` (it multiplies the current baseline by the trip count) is not fixed here; no requirement was newly verified |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 009 - 2026-10-27 - Fix cumulative difference across trips

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Fix the cumulative-difference bug and add tests. |
| Constraining sources | SRD 2.1.6 (cumulative difference from the always-drive baseline); the issue recorded in entry 008 |
| What it produced | `c3 update_trends` now sums each stored trip's own baseline (distance x drive factor) minus its estimate, instead of multiplying the latest baseline by the trip count; `update_trends` no longer takes a baseline argument and `c2 compare_baseline` calls it without one; `tests/test_trends.py` (3 tests; two fail on the previous code with -1152 instead of 384) |
| Not claimed | Weekly and monthly totals still sum all stored trips with no date windowing; factors remain placeholders |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 010 - 2026-10-27 - Route comparison page with OpenRouteService adapter and fallback

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Next step: replace typed distance with start and destination, show drive, walk and bike per mode, use OpenRouteService, and keep the demo working when a call fails. |
| Constraining sources | Team discussion (distance differs by mode; transit entered by the user later); ORS v2 conventions from public forum threads, not the official reference |
| What it produced | `src/c3_data_adapter/route_adapter.py` (geocode, per-mode routes, per-mode fallback); `src/c2_application_service/comparison.py` (`compare_modes`); new types in `src/interfaces.py`; `/compare` page, `base.html` shared layout; `tests/test_routes.py` and two web tests; ADR 0003; README section |
| Not claimed | One live call was made afterwards with the team's free key (place search and the three profiles worked on the old host; the announced new host returned 404); automated tests use mocks only; fallback detour factors and speeds are assumptions; no weather or feasibility filtering yet; transit and the Innoslate model are not updated; the new functions carry no `@realizes` tags |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 011 - 2026-10-27 - Feasibility filter, weather and recommendation on the compare page

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Continue: add weather, the Commuter's not-feasible settings and a manually entered bus time so the compare page recommends a mode and says why. |
| Constraining sources | Team discussion ("best" means feasible under weather, carbon and time, not cheapest); Open-Meteo `current` response checked once live on 2026-10-27 |
| What it produced | `src/c3_data_adapter/weather_adapter.py`; `src/c2_application_service/recommendation.py` and `plan.py`; `explain_recommendation` in C.4; optional bus time and limits in `compare_modes` and the page; new types in `src/interfaces.py`; `tests/test_recommend.py` and two web tests; ADR 0004; README paragraph |
| Not claimed | The thresholds (0.1 mm rain, 0 C, 40 km/h wind, 10 extra minutes) are project assumptions, not safety guidance; weather is current conditions at the start, not the forecast for the trip time; bus distance is assumed equal to the drive route and its factor is a placeholder; no daylight, elevation or accessibility rules yet; the Innoslate model and the new functions' `@realizes` tags are not updated; the explanation is a fixed template, not a language model |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 012 - 2026-10-27 - Badges, trip confirmation and campus tree progress

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Implement the badges and the campus tree progress with the proposed default conditions. |
| Constraining sources | Team discussion of eight badge conditions and a tree goal; the proposal that earlier badge wording (Five Day Flow, Car-Free Week) be tightened against easy gaming |
| What it produced | `src/c2_application_service/achievements.py`, `confirmation.py`, `demo_data.py`; `src/c3_data_adapter/trip_store.py`; new types in `src/interfaces.py`; `/confirm`, `/achievements`, `/demo`, `/reset` routes and `achievements.html`; confirm buttons and a date field on `/compare`; `tests/test_achievements.py` (22 tests); ADR 0005; README paragraph |
| Not claimed | The 22 kg per tree, all badge thresholds and the caps are project assumptions, and the per-tree figure has no cited source yet; the campus share and the sample trips are invented and labelled as such; one demo Commuter, in memory only; the Log a trip page does not feed badges; the model and `@realizes` tags are not updated |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 013 - 2026-10-27 - Plan-first flow, done page with badge popup, garden page and a playful style

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | After previewing the pages: always require a start and destination and compare first, then choose a way; after choosing show a congratulation page and pop up a badge if one is earned (not jump to the achievements page); make Achievements a place to review trips and see goals not yet reached; add a garden page where each tree the campus has earned is drawn, with small animations; make the style less plain. |
| Constraining sources | The existing C.2 plan, confirmation and badge rules (unchanged); the conversation about the intended flow |
| What it produced | `src/c1_web_front_end/web_app.py` rewritten (plan, confirm, `/done/<n>`, achievements, garden); templates `base.html` (new style and animations), `_macros.html`, `plan.html`, `done.html`, `achievements.html`, `garden.html`; the old `commute.html`, `compare.html` and the typed-distance web form removed; tests updated (`test_web_app.py`, `test_achievements.py`) |
| Not claimed | C.2 and C.3 rules are unchanged (thresholds, factors and the 22 kg per tree are still assumptions); the removed web form was the browser version of UC.1, whose command-line path remains; traceability documents were not updated for the removed page; the design was checked in one browser only, and the dark-mode look was not viewed |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 014 - 2026-10-27 - Traceability notes for the web pages

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Continue with the follow-ups: check dark mode and bring the traceability notes up to date. |
| Constraining sources | `docs/traceability.md`, `docs/walking-skeleton.md`, the current code and tests |
| What it produced | A table of the browser pages with their code and tests; open item O-4 reworded and O-9 added (the new flow is not in the Innoslate model); the C.1 row of the walking-skeleton table corrected |
| Not claimed | No requirement or model element was added or linked; the dark-mode look was checked by eye on the garden page only; the ORS host move to `api.heigit.org` was not re-checked (needs the team's key) |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 015 - 2026-10-27 - Model 10.9: needs, requirements, route service and UC.3 for the web flow

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Add the web flow to the Innoslate model and the requirements (open item O-9); choose whatever numbering is most sensible. |
| Constraining sources | The model's own numbering and relationship patterns in export 10.8; SPEC.md format; ADR 0002, 0003, 0005; the current code |
| What it produced | `docs/model/scripts/build_model_10_9.py` and its output `docs/model/EcoCommute_10.9_web_flow.xml` (47 new elements: 4 needs, 5 stakeholder requirements, 14 system requirements, X.6, 2 conduits, 6 input/outputs, UC.3 with 11 steps, 3 risks, all linked in both directions); SPEC.md entries 2.1.11-2.1.14 and 2.2.5; `docs/model/10.9-changes.md`; `@realizes("UC.3.x")` tags on the implementing functions; `web_app.py` views moved to module level so they can be tagged; `tests/test_model_10_9.py` and a UC.3 section in `tests/test_model_linkage.py`; traceability, README updates |
| Not claimed | **The 10.9 file has not been imported into Innoslate**; its structure was checked by script and tests only. New requirements are Drafts with every quality flag false. The allocation of the new functional requirements to F.2.3-F.2.6 is provisional and the function architecture was not extended. The 80% target, the two-trips-per-day and 50 km limits and the 22 kg per tree are assumptions, the last without a source. The Chapter 4-7 reports were not updated. Risks TR.10-TR.12 record gaps found while writing (place labels vs coarse location; Route Service dependence; unsourced tree conversion), not decisions |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 016 - 2026-10-27 - Fix the two Intelligence errors found on importing model 10.9

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | The Innoslate Intelligence dashboard for the imported 10.9 (screenshot): pass rate 77%, with errors on UC.3. |
| Constraining sources | The screenshot of the Intelligence dashboard; the model data of 10.8 and 10.9 |
| What it produced | `build_model_10_9.py` fixed and the export regenerated: UC.3.10 no longer receives a flow from UC.3.8 ("prior action is dependent on the later action"), and UC.3, UC.3.1 and UC.3.11 now satisfy requirements; SPEC.md "satisfied by" lines and `docs/model/10.9-changes.md` updated; two regression tests in `tests/test_model_10_9.py` |
| Not claimed | The cause of the first error is inferred (string order puts UC.3.10 before UC.3.8); Innoslate's own rule was not seen. The warning lists were read only as counts in the screenshot, so "same as 10.8" is checked for four heuristics and not for the others. Afterwards the team re-imported the corrected file and reported (screenshot) a pass rate of 81% with no errors; the remaining warnings were not examined one by one |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 017 - 2026-10-27 - Place suggestions while typing

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/web-app` |
| Prompt (summary, originally Chinese) | Typing "upson hall" found no place; show close matches to pick from while typing. |
| Constraining sources | The existing plan page and route adapter; ORS geocoder conventions (autocomplete endpoint, Pelias-style focus point) |
| What it produced | `suggest_places` in `route_adapter.py` (sample matches first, then ORS autocomplete biased to the campus, cached, capped at 5); `geocode` resolves a picked suggestion to the same point and matches a single unambiguous sample place by words; four more approximate sample places (Upson, Duffield, Olin Library, Willard Straight); `/places?q=` JSON endpoint; a small script on `plan.html` that refreshes the suggestion list (250 ms pause, late answers ignored); tests in `tests/test_routes.py` and `tests/test_web_app.py` |
| Not claimed | The unit tests mock ORS. Afterwards one live check with the team's key (not stored in the repository) returned HTTP 200 on `api.openrouteservice.org` for `/geocode/autocomplete` ("statler hall" gave Statler Hall, Ithaca) and `/geocode/search` ("upson hall cornell" gave Upson Hall, Ithaca first); the same paths on `api.heigit.org` returned 404. The page's own request with the `focus.point` parameters was not exercised end to end in the browser with a key. Without a key only the eight sample places can be suggested. The new sample coordinates are approximate and unverified. The suggestion list is the browser's own list, so its look and keyboard behaviour differ by browser |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 018 - 2026-10-27 - Google-Maps-style place picker with a map

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/place-picker` |
| Prompt (summary, originally Chinese) | Searching a place should work like Google Maps: a list of close matches to choose from, a map showing where it is, and it must work for places never typed before (Statler Hall was not found). |
| Constraining sources | The merged plan page and route adapter; Leaflet 1.9.4 from cdnjs; OpenStreetMap tiles |
| What it produced | A custom suggestion list on the From and To boxes (name plus where it is, arrow keys, Enter, Escape, picked box turns green); a map card with a pin for the start and a flag for the destination that fits both; `/places` now returns label and coordinates; a line on the page saying whether place search is live (key set) or limited to the sample places; a routed result replaces the sample entry for the same place; tests in `tests/test_web_app.py` and `tests/test_routes.py` |
| Cause found for the missing Statler Hall | The server the Commuter was using had no `ORS_API_KEY`, so only sample places could be found; with the key, `statler hall` resolves to Statler Hall, Ithaca (checked). A second, older server was also still listening on port 5000 and answered first |
| Not claimed | The map needs internet for the Leaflet files and OpenStreetMap tiles (without it the page works and the map card stays hidden); OpenStreetMap's tile policy allows light use only, so a deployed demo with many users would need a tile provider; Leaflet is loaded without an integrity hash; keyboard use of the list was coded but only mouse and typing were exercised in the browser; place search results are ORS's ranking, so ambiguous names can list places elsewhere (for example "Upson County, GA") |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 019 - 2026-10-27 - Server finds the ORS key without a fresh terminal

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/place-picker` |
| Prompt (summary, originally Chinese) | The page says "Offline list only (no ORS key set)"; is the connection failing? Fix it. |
| Constraining sources | The screenshot of the page; the saved Windows user variable |
| What it produced | `src/key_loader.py`: at server start, use `ORS_API_KEY` from the process, else a git-ignored `.env` file, else the Windows user environment; `src/main_web.py` calls it and prints which source was used (never the key); `tests/test_key_loader.py` (5 tests, no real key or registry); README paragraph |
| Cause | Not the network. The terminal that started the server was opened before the variable was saved, so it did not have it; a Windows user variable reaches only programs started afterwards |
| Not claimed | Checked by starting a process with the variable removed: the loader found the key in the Windows user environment and place search returned Statler Hall. The registry lookup works on Windows only. Only the entry point calls the loader, so other ways of starting the app (for example `flask run`) still need the variable in the process |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 020 - 2026-10-27 - Map opens on the Commuter's location and draws the three routes

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/place-picker` |
| Prompt (summary, originally Chinese) | Open with the map on the current location; after the places are filled in, mark the start and the destination and draw the routes between them, possibly drive, walk and bike at once; propose improvements. |
| Constraining sources | ORS Directions GeoJSON answers checked live on 2026-10-27 (LineString, lon/lat order, `properties.summary`); the browser Geolocation API |
| What it produced | Routes now carry a `path` (ORS `/geojson` endpoint; a straight line for the estimate fallback); C.3 asks for the three modes in parallel and remembers all-ORS answers; C.2 `preview_routes`; `/route-lines` JSON endpoint; the map card is open by default, asks the browser for the position, shows a "you are here" dot, a *Start from my location* button (label `My location (lat, lon)`, resolved without a search service), pins for start and destination, three route styles with a legend; fix for `hidden` being overridden by button styles; tests in `tests/test_routes.py` and `tests/test_web_app.py` |
| Not claimed | The browser pane here denied location, so the success path was exercised by replacing the position with a fixed one near Collegetown, not by a real device fix; desktop browsers can be less exact than a phone; the page loads Leaflet and OSM tiles from the internet; the first drive request after idle took about 3.5 s in one timing, later ones about 0.5 s; routes are shown only for the three modes ORS covers (no bus line); the position is sent to this server only when it is used as the start, and then to ORS as a route coordinate |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 021 - 2026-10-27 - Student defaults, vehicles and a reserved bus card

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/student-defaults` |
| Prompt (summary, originally Chinese) | Put "Start from my location" under the start box, not on the map; remove the example routes; assume the student has no bike and rank bike after walk; replace the limits with only "I have a bike" and "I have a scooter" and rename the section; remove the bus minutes and extra-minutes boxes; reserve a bus card on the compare page for data later; fix other UI that does not match how it is used. |
| Constraining sources | The previous plan page and ADR 0004; the team's choices in the prompt |
| What it produced | `plan_commute(origin, destination, have=())` (vehicles only when ticked); scooter row built from the bike route; walk and wheeled time limits and the priority order in `recommend_mode`; a fallback wording when only driving is left; scooter factor and emoji; the form (From box, button under it, "What I have with me", offline warning only when offline); one confirm form with the date next to the way cards; a disabled "Coming soon" bus card; map lines and legend follow the ticked vehicles; ticks remembered in the browser; Enter in the date box no longer picks a way; `have` values are filtered on the server; ADR 0006; tests updated and added (125 pass) |
| Not claimed | The thresholds (30 min walk, 45 min bike or scooter), the scooter factor (20 g per km) and the scooter using the bike route and speed are project assumptions. **SPEC.md 2.1.11 and model 10.9 still describe a typed bus time and were not changed**; the team must update them. Weather rules are unchanged. The scooter is assumed electric. Checked in the in-app browser at a narrow width; position was simulated; the card pop-in animation was caught mid-way in one screenshot |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 022 - 2026-10-27 - TCAT bus schedule from the real GTFS feed

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/tcat-transit` |
| Prompt (summary, originally Chinese) | Build the bus part on TCAT's own data, with real routes, stops, shapes, direction and which routes run on which days (some stop on weekends); raise other points to watch. |
| Constraining sources | The TCAT GTFS zip downloaded from `s3.amazonaws.com/tcat-gtfs/tcat-ny-us.zip` on 2026-10-27 (1.5 MB, feed version 20260922); the Mobility Database listing of the feed (no licence stated) |
| What it produced | `src/c3_data_adapter/gtfs_store.py` (import to SQLite, unit detection, service days, queries) and `src/update_transit.py` (download and build); `src/c2_application_service/bus_planner.py` (direct rides, after-midnight trips, reasons for no bus); the bus row in `plan_commute` and `confirm_trip`; the "Leaving" field, a real bus card, bus line and stops on the map, `/route-lines` with the bus; ADR 0007; `tests/gtfs_fixture.py` (an invented feed with the same quirks) and `tests/test_transit.py`, plus web tests; startup line about the schedule; `tzdata` for Windows; `data/` git-ignored |
| Findings from the data | Distances are in feet (found by comparing with the drawn lines; read as metres they would be 3.28 times too long); 23,534 stop times are past 24:00:00; one service per weekday group and one exception (2026-11-26, no service); routes 10, 36, 65, 81 and 82 have no weekend service, 115 runs only at weekends; wheelchair and bike fields are all unknown; no transfers or real-time feed |
| Not claimed | Direct rides only, no transfers; walking legs are straight lines times 1.25; the bus factor is still the placeholder 105 g per km; the schedule is not live; the feed's terms of use were not found, so the data is not committed; walking speed, 900 m reach and the one-minute slack are project assumptions; checked against the real feed at a few places and times, not against TCAT's own trip planner; **SPEC.md 2.1.11 and model 10.9 still describe a typed bus time and were not changed** |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 023 - 2026-10-28 - Bus route choice, carpool share and faster place suggestions

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/choices-and-speed` |
| Prompt (summary, originally Chinese) | Several bus routes can link the same places (for example Cayuga Place to Upson): let the student choose; under the drive card offer alone or carpool with a number of people; make the suggestions under the start and destination boxes appear faster. |
| Constraining sources | The TCAT feed already built (ADR 0007); live calls to the OpenRouteService geocoder and directions on 2026-10-28 |
| What it produced | `bus_planner`: the best ride of each route, within an hour of the best, at most 5; `plan_commute(..., bus_route)`, `confirm_trip(..., occupants, bus_route)`; the bus card with a route pick that switches the card and the map line; the drive card with Alone or Carpool and live numbers; carpool recorded as its own way with people and the share of emissions; a drive and a carpool of one trip count once; trips remember the bus route; `route_adapter`: kept-open shared connections with warm-up, quick local answers first, prefix reuse, a pause after quota or rate-limit answers, separate autocomplete / search / route quotas, search as a fallback for autocomplete, near-campus first; the page script shows a list at once and the online one after 150 ms, cancelling stale requests; ADR 0008; tests (254 pass) |
| Found while checking | The team key's autocomplete quota was used up (403 "Quota exceeded", unchanged after 70 s, so a daily quota; search still worked). A first version of the faster HTTP helper sent `Accept: application/json`, which made the GeoJSON route service answer 406 and every route fall back to an estimate; mocked tests did not show it, a live check did, and the header is no longer sent (a local-server test guards it). Searching "cayuga place" near campus finds no place of that name, only Cayuga Trail, Street and Heights |
| Not claimed | The people range (2 to 8), the one-hour option window, the 25 km radius and the 150 ms delay are project assumptions; occupants are self-reported; timing figures come from a few runs on one machine; my own testing used part of the free quota; SPEC.md and model 10.9 do not describe the carpool share or the bus choice |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 024 - 2026-10-28 - Invite-only accounts, saved trips and a persistent place cache

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/accounts` (stacked on `feat/choices-and-speed`, PR 20) |
| Prompt (summary, originally Chinese) | Keep accounts and records between runs; use invite codes (at least one per team member plus three for the professor and TA); let teammates use the site while the terminal runs on the owner's computer, not the open internet; no email verification; keep places that were searched so they are not searched again. |
| Constraining sources | The team's choices in the prompt; the earlier discussion of risks of a public site |
| What it produced | `src/c3_data_adapter/app_db.py` (SQLite file, schema, backup); `src/c2_application_service/accounts.py` (scrypt passwords, invites stored as hashes, sign-up and log-in limits, lockout, password change, delete, preferences; standard library only); `trip_store.py` with an in-memory and an SQLite per-account store and the other accounts' totals; the shared tree over all accounts; `src/c1_web_front_end/auth.py` (signed sessions, form tokens, page guards, security headers, log-in, sign-up, account, export pages); templates; per-account preferences and recent trips; `persistent_cache.py` and its use in the route adapter (suggestions, looked-up places, routes between known places); `src/manage.py`; `main_web.py` options (`--host`, `--port`, waitress, start-up lines); ADR 0009; README sections; about 120 new tests (381 in all) |
| Found while testing | An empty form token matched an empty session token, so a browser without a session could post the log-in form (fixed and tested). A failed invite attempt was recorded inside a transaction that the raised error rolled back, which would have disabled the guessing limit (fixed and tested). Checked against a fresh database in the browser: invite sign-up, saving a trip, restarting the server (still signed in; trips, vehicles and recent trip kept), isolation from another account, and that the Content-Security-Policy lets the map load |
| Not claimed | Not a security review. Follow-up the same day (team request): the invite system was simplified to three shared codes (team members, project manager, professor), the sign-up form became user name, password, password again, invite code, the sign-up limits were removed because the site is private, the password rule was relaxed to 6 characters, and `manage seed` creates the named accounts from a git-ignored roster file. The log-in lockout (5 wrong passwords, 15 minutes) is a project assumption for a small invited group. Tailscale and tunnel use is described but was not tried here. Plain http on a shared network is readable by others. The database holds personal data: whether the course allows keeping real people's trips was not checked. SPEC.md and model 10.9 do not describe accounts or invites. Timing of the test suite grew (about 30 s) |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 025 - 2026-10-29 - Model 11.0: bus timetable, vehicles, carpool, place suggestions and accounts

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `docs/model-10-10-accounts-transit` (from `origin/main`) |
| Prompt (summary, originally Chinese) | The project changed a lot; update Innoslate. The assistant cannot sign in to Innoslate, so the team chose: change the repository's model XML and sync the documents; the team imports it. |
| Constraining sources | Model 10.9 and `build_model_10_9.py` (numbering and relationship patterns); prompt-log entries 017-024 and ADRs 0006-0009 (what the app gained); SPEC.md; the current code |
| What it produced | `docs/model/scripts/build_model_11_0.py` and its output `docs/model/EcoCommute_11.0_accounts_transit.xml` (45 new entities, 276 new relationships: 4 needs, 5 stakeholder requirements, 16 system requirements, X.7, a conduit, 5 input/outputs, UC.3.12-UC.3.15, UC.4 with 5 steps, 3 risks; 2.1.11 and 3.3.1.9 reworded); `docs/model/11.0-changes.md`; SPEC.md entries 2.1.15-2.1.18, 2.3.8 and the reworded 2.1.11; `@realizes` tags (UC.3.14 on `find_bus`, formerly UC.3.4; UC.3.15, UC.4.3, UC.4.4, UC.4.5); `tests/test_model_11_0.py` and a UC.4 section in `tests/test_model_linkage.py`; traceability (section and O-11), context and README pointers |
| Not claimed | The first import of 11.0 gave Intelligence 74% with three errors (two input/outputs without a requirement; "prior action is dependent on the later action" on UC.3 and UC.4, cause inferred); the file was corrected and imported again (76%, one error: looping input/outputs on Trip Options, cause not understood); the cause was then found in Innoslate's Fix dialog (the parent actions UC.3 and UC.4 had no timeline in their simulation data; pure 10.9 had the same error) and fixed in the file; **the final file was imported into a new project: Intelligence 77%, no errors, warnings only**. New requirements are Drafts with every quality flag false. The function architecture and the Chapter 4-7 reports were not updated. The numbers (2 to 8 people, 5 wrong passwords in 15 minutes, 90% suggestion rate, no vehicle by default) are proposals. Carpool, the place cache and the lockout have no use-case step of their own |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry template

| Field | Value |
|---|---|
| Date / tool / model | |
| Requested by / branch | |
| Prompt (verbatim or summary) | |
| Constraining requirement/spec text (IDs) | |
| What it produced (files) | |
| Human review (who, when, what changed) | |
