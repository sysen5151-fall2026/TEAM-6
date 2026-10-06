# Model-to-product traceability

Chain: **Stakeholder -> Need (SND 1.x.x) -> Requirement (SRD 2.x.x, in [SPEC.md](../SPEC.md)) -> UC.1 action -> code -> test.**
Requirement-to-action links come from the `satisfies` relationships in the Innoslate export `EcoCommute 10.4.xml`.

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

## Requirements not exercised by the skeleton

Institutional (2.2.x: UC.2), operational and retirement (2.1.7, 2.1.8, 2.3.x, 2.5.1, 2.5.2: OP.1-OP.5) requirements are outside the UC.1 nominal path; SPEC.md marks them "Not in skeleton". No code claims to implement them.

## Open items (honest gaps)

| ID | Item | Action / owner |
|---|---|---|
| O-1 | ~~C.4 had no need or requirement.~~ **Closed:** need 1.1.8 and requirement 2.1.10 added (SPEC.md, Innoslate model 10.6); C.4 performs UC.1.11. Remaining: the real language-model call is still a stub. | Later increment. |
| O-2 | Emission factors are placeholders (`version stub-0`), so 2.4.1 is only partially met. | Method Reviewer supplies the reviewed factor table. |
| O-3 | Occupancy is not handled (BMA 7.8 open item); the "under 3 km and no rain" rule threshold is unvalidated. | Method reviewer / product lead. |
| O-4 | No web UI, so 2.1.1 timing, 2.1.9 (WCAG) and 2.5.3 cannot be tested yet. | Next increment. |
| O-5 | Off-nominal paths (weather outage, invalid input) are neither modeled nor coded. | Add to model first, then code. |
| O-6 | System requirements for SH.6/SH.7 needs (BMA N11) are deferred to Architecture Definition. | Add to SPEC as 3.x.x. |
| O-7 | C.1-C.4 were missing from the Innoslate export (only C.0). **Closed:** fixed in the export, and the 10.6 export (adds 1.1.8 / 2.1.10) was imported; Intelligence shows no errors, only warnings (81% pass; `docs/model/intelligence-10.6.webp`). Remaining: redraw the context, hierarchy and action diagrams with C.1-C.4. | Yiyang Zou, by Oct 14. |
