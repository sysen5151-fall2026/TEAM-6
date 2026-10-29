# Model-to-product traceability

Chain: **Stakeholder -> Need (SND 1.x.x) -> Requirement (SRD 2.x.x, in [SPEC.md](../SPEC.md)) -> UC.1 action -> code -> test.**
Requirement-to-action links come from the `satisfies` relationships in the Innoslate export `docs/model/EcoCommute_10.6_C4-explanation-req.xml`; the current export, `docs/model/EcoCommute_10.7_C4-C5_system_requirements.xml`, keeps these links and adds the system requirements (3.x.x) and the F.x functions that satisfy them (report in `docs/ch4-ch5/`).

## Worked example (the one to show live)

SH.1 Commuters -> need **1.1.4 Get advice I can use** ("I need suggestions for a greener way to travel that fit the weather and my own limits, so I get advice I can actually follow.") -> requirements **2.1.4** (one alternative with a stated reason from distance, forecast weather and feasibility settings) and **2.1.5** (never recommend a mode marked not feasible) -> actions **UC.1.6, UC.1.7, UC.1.10** (and UC.1) -> `c3_data_adapter.request_weather`, `x3_open_meteo_stub.return_weather_forecast`, `c2_application_service.evaluate_alternatives` -> tests `test_short_dry_trip_gets_walk_alternative`, `test_infeasible_mode_is_never_recommended`, `test_rain_blocks_walk_bike`.

A second chain: need **1.1.1 Log my commute quickly** -> **2.1.1** (30 s or less for 80% of timed tasks) -> UC.1.1-UC.1.4 -> `open_commute_entry`, `present_entry_fields`, `enter_trip_details`, `submit_commute_request` (timing not measurable until there is a real UI).

A third chain (added in model 10.6): SH.1 -> need **1.1.8 Understand my result in plain words** -> requirement **2.1.10** (explanation states only facts from the calculated result) -> action **UC.1.11** (performed by C.1 and C.4) -> `c4_explanation_model.explain_result` -> test `test_explanation_contains_required_facts` (estimate, baseline, difference, factor source and version, reason all present) and `test_explanation_states_only_calculated_facts` (no figure that is not in the calculated result).

## UC.1 action to code

| Action | Performer | Code | Requirements (model) | Test |
|---|---|---|---|---|
| UC.1.1 Open Commute Entry | X.1 | `x1_commuter_sim.open_commute_entry` | 2.1.1 | end-to-end |
| UC.1.2 Present Entry Fields | C.0 | `c1_web_front_end.present_entry_fields` | 2.1.1, 2.1.9, 2.5.3 | end-to-end |
| UC.1.3 Enter Trip Details | X.1 | `x1_commuter_sim.enter_trip_details` | 2.1.1, 2.5.3 | end-to-end |
| UC.1.4 Submit Commute | X.1 | `c1_web_front_end.submit_commute_request` | 2.1.1 | end-to-end |
| UC.1.5 Accept Entry and Retrieve Factor | C.0 | `c2...process_commute`, `c3...retrieve_factor` | 2.4.1 | `test_result_discloses_method_and_labels_estimate` |
| UC.1.6 Request Weather | C.0 | `c3...request_weather` | 2.1.4 | `test_rain_blocks_walk_bike` |
| UC.1.7 Return Weather Forecast | X.3 | `x3_open_meteo_stub.return_weather_forecast` | 2.1.4 | `test_rain_blocks_walk_bike` |
| UC.1.8 Estimate Emissions and Store Trip | C.0 | `c2...estimate_emissions`, `c3...store_trip` | 2.1.2, 2.4.2 | `test_primary_path_runs_and_returns_result` |
| UC.1.9 Update Trends and Compare Baseline | C.0 | `c2...compare_baseline`, `c3...update_trends` | 2.1.2, 2.1.6, 2.4.3 | `test_baseline_difference_for_greener_mode` |
| UC.1.10 Evaluate Feasible Alternatives | C.0 | `c2...evaluate_alternatives` | 2.1.4, 2.1.5 | `test_short_dry_trip_gets_walk_alternative`, `test_infeasible_mode_is_never_recommended`, `test_long_trip_gets_no_alternative` |
| UC.1.11 Display Commute Result | C.1, C.4 | `c1...display_commute_result`, `c4...explain_result` | 2.1.2, 2.1.3, 2.1.9, 2.1.10, 2.4.4 | `test_result_discloses_method_and_labels_estimate`, `test_explanation_contains_required_facts`, `test_explanation_states_only_calculated_facts` |
| UC.1.12 Review Result | X.1 | `x1_commuter_sim.review_result` | 2.1.2 | end-to-end |

`tests/test_model_linkage.py` reads the UC.1.x actions from the exported model in `docs/model/` and checks that each has `@realizes`-tagged code and that no other UC.1 ID is tagged (it does not check performers or satisfies links).

## Web pages and use case UC.3 (draft model 10.9)

The browser pages go beyond the modeled UC.1 log-a-trip flow. Model 10.9 ([docs/model/10.9-changes.md](model/10.9-changes.md)) adds the needs, requirements and use case UC.3 for them as **drafts imported into Innoslate; Intelligence gave 81% with no errors after two errors in the first import were fixed**. Chain: need 1.1.9 Compare every way before I choose -> requirement **2.1.11** -> system requirements 3.1.1.8, 3.1.1.9, 3.1.2.5, 3.1.2.6, 3.2.9, 3.2.10, 3.3.1.9 -> actions **UC.3.2-UC.3.6** -> `route_adapter.get_route_options`, `compare_modes`, `recommend_mode`, `render_plan` -> tests in `tests/test_web_app.py` and `tests/test_routes.py`. Needs 1.1.10 / 1.1.11 / 1.2.4 lead to 2.1.12-2.1.14 and 2.2.5 the same way.

| Action | Performer | Code | Requirements (model 10.9) | Test |
|---|---|---|---|---|
| UC.3.3 Request Routes | C.3 | `c3...geocode`, `get_route_options` | 2.1.11 | `tests/test_routes.py` |
| UC.3.5 Compare Modes and Recommend | C.2, C.4 | `c2...compare_modes`, `recommend_mode`, `plan_commute`; `c4...explain_recommendation` | 2.1.11, 2.1.4, 2.1.5 | `tests/test_routes.py`, `tests/test_recommend.py`, `tests/test_web_app.py` |
| UC.3.6 Present Comparison | C.1 | `c1...web_app.render_plan` | 2.1.11 | `tests/test_web_app.py` |
| UC.3.8 Record Trip and Update Progress | C.2, C.3 | `c2...confirm_trip`, `c3...add_confirmed` | 2.1.12, 2.1.13, 2.1.14, 2.2.5 | `tests/test_achievements.py` |
| UC.3.9 Display Trip Result and Badges | C.1 | `c1...web_app.done_page` | 2.1.13 | `tests/test_achievements.py` |
| UC.3.10 Present Progress Pages | C.1, C.2 | `c1...web_app.achievements_page`, `garden_page`; `c2...evaluate_badges`, `campus_goal` | 2.1.13, 2.2.5 | `tests/test_achievements.py` |

UC.3.1, UC.3.2, UC.3.7 and UC.3.11 are performed by the Commuter and UC.3.4 by the Route Service, so no code claims them. `tests/test_model_linkage.py` checks the rest against the model, and `tests/test_model_10_9.py` checks the structure of the 10.9 file.

## Bus, vehicles, accounts and place suggestions (draft model 11.0)

Model 11.0 ([docs/model/11.0-changes.md](model/11.0-changes.md)) adds what the app gained after 10.9 as **drafts, imported into a new project: Intelligence 77%, no errors (warnings only)**: needs 1.1.12-1.1.14 and 1.3.5, requirements 2.1.15-2.1.18 and 2.3.8, 16 system requirements, X.7 Transit Schedule Publisher, UC.3.12-UC.3.15, UC.4 Sign Up and Log In, and risks TR.13-TR.15. Chain example: need 1.1.12 Plan with the real bus schedule -> requirement **2.1.15** -> system requirements 3.1.1.11, 3.1.2.9, 3.2.11, 3.3.1.13, 3.4.6.3 -> actions **UC.3.13, UC.3.15** -> `bus_planner.find_bus` -> `tests/test_transit.py`, `tests/test_bus_options.py`.

| Action | Performer | Code | Requirements (model 11.0) | Test |
|---|---|---|---|---|
| UC.3.13 Plan Bus Ride | C.2 | `c2...bus_planner.find_bus` (was tagged UC.3.4, which is the Route Service's step) | 2.1.15 | `tests/test_transit.py`, `tests/test_bus_options.py` |
| UC.3.14 Suggest Places | C.3 | `c3...route_adapter.suggest_places` | 2.1.18 | `tests/test_routes.py`, `tests/test_web_app.py` |
| UC.4.3 Verify Invite Code and Credentials | C.2 | `c2...accounts.register`, `authenticate` | 2.3.8, 2.1.17 | `tests/test_accounts.py`, `tests/test_auth_web.py` |
| UC.4.4 Store Account and Trips | C.3 | `c3...app_db.connect` (opens and creates the account file) | 2.1.17 | `tests/test_accounts.py` |
| UC.4.5 Present Signed-in Pages | C.1 | `c1...auth.init_auth` (guards, log-in, sign-up and account pages) | 2.1.17 | `tests/test_auth_web.py` |

UC.3.15 is the transit agency's step, UC.3.12 the Commuter's choice of vehicles and sharing (the carpool share itself is computed in `confirm_trip`, already UC.3.8), and UC.4.1 and UC.4.2 the Commuter's, so no code claims them. `tests/test_model_linkage.py` checks the rest against the model, and `tests/test_model_11_0.py` checks the structure of the 11.0 file.

## Requirements not exercised by the skeleton

Institutional (2.2.x: UC.2), operational and retirement (2.1.7, 2.1.8, 2.3.x, 2.5.1, 2.5.2: OP.1-OP.5) requirements are outside the UC.1 nominal path; SPEC.md marks them "Not in skeleton". No code claims to implement them.

## Open items (honest gaps)

| ID | Item | Action / owner |
|---|---|---|
| O-1 | ~~C.4 had no need or requirement.~~ **Closed:** need 1.1.8 and requirement 2.1.10 added (SPEC.md, Innoslate model 10.6); C.4 performs UC.1.11. Remaining: the real language-model call is still a stub. | Later increment. |
| O-2 | Emission factors are placeholders (`version stub-0`), so 2.4.1 is only partially met. | Method Reviewer supplies the reviewed factor table. |
| O-3 | Occupancy is not handled (BMA 7.8 open item); the "under 3 km and no rain" rule threshold is unvalidated. | Method reviewer / product lead. |
| O-4 | A web UI now exists (Flask, ADR 0002), but 2.1.1 timing, 2.1.9 (WCAG) and 2.5.3 have not been measured or audited against it; the pages were only checked by hand in one browser. | Measure and audit next. |
| O-5 | Off-nominal paths (weather outage, invalid input) are neither modeled nor coded. | Add to model first, then code. |
| O-6 | System requirements for SH.6/SH.7 needs (BMA N11) are deferred to Architecture Definition. | Add to SPEC as 3.x.x. |
| O-7 | C.1-C.4 were missing from the Innoslate export (only C.0). **Closed:** fixed in the export, and the 10.6 export (adds 1.1.8 / 2.1.10) was imported; Intelligence shows no errors, only warnings (81% pass; `docs/model/intelligence-10.6.webp`). Remaining: redraw the context, hierarchy and action diagrams with C.1-C.4. | Yiyang Zou, by Oct 14. |
| O-8 | The Chapter 4 first-level functions F.2.0-F.2.7 are not yet mapped to modules or mechanisms (eight functions against components C.1-C.4); no requirement or test columns for the 3.x.x system requirements yet. | Allocate functions to mechanisms and extend this table in the next chapter (risk TR.9 in the Chapter 4-5 report). |
| O-9 | The web flow (plan, choose, done, garden, achievements), the Route Service, badges and the campus tree goal are now **drafted in model 10.9** (needs 1.1.9-1.1.11, 1.2.4; requirements 2.1.11-2.1.14, 2.2.5 and 14 system requirements; X.6; UC.3; TR.10-TR.12) and the file was imported (Intelligence 81%, no errors), but the function architecture was not extended, and the Chapter 4-7 reports describe 10.7 and 10.8. | The team decides whether the web flow needs functions of its own. |
| O-10 | Confirmed trips keep the start and destination labels, finer than the coarse location 2.5.1 and 3.4.5.2 require (risk TR.10); the 22 kg per tree has no cited source (TR.12). | Decide what location detail is stored; cite or replace the conversion. |
| O-11 | Bus, vehicles, carpool, place suggestions and accounts exist in the app and are **drafted in model 11.0** (imported: Intelligence 77%, no errors); no new F.x functions were added. TR.13-TR.15 record the unknown timetable terms, the personal data held on one computer and the shared invite codes. | Import 11.0 and read Intelligence; the team decides whether bus and accounts need functions of their own. |
