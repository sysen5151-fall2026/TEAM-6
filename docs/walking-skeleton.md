# Walking skeleton: UC.1 Review Commute Impact and Feasible Alternative

One user action traverses the interface, service, data/weather and decision participants and returns a correctly shaped Commute Impact Result. The call order follows the Sequence Diagram and action list of the model (BMA Sections 7.3 and 7.7). Run it with `python -m src.main`.

## Call order

| Step | Model action | Performer | Code |
|---|---|---|---|
| 1 | UC.1.1 Open Commute Entry | X.1 Commuter | `x1_commuter_sim.open_commute_entry` |
| 2 | UC.1.2 Present Entry Fields | C.0 (C.1) | `c1_web_front_end.present_entry_fields` -> **Entry Form** |
| 3 | UC.1.3 Enter Trip Details | X.1 Commuter | `x1_commuter_sim.enter_trip_details` -> **Entry Request** |
| 4 | UC.1.4 Submit Commute | X.1 Commuter | `x1_commuter_sim.run_uc1` -> `c1_web_front_end.submit_commute_request` -> **Commute Request** |
| 5 | UC.1.5 Accept Entry and Retrieve Factor | C.0 (C.2, C.3) | `c2_application_service.process_commute`, `c3_data_adapter.retrieve_factor` |
| 6 | UC.1.6 Request Weather | C.0 (C.3) | `c3_data_adapter.request_weather` -> **Weather Query** |
| 7 | UC.1.7 Return Weather Forecast | X.3 Open-Meteo | `x3_open_meteo_stub.return_weather_forecast` -> **Weather Forecast** |
| 8 | UC.1.8 Estimate Emissions and Store Trip | C.0 (C.2, C.3) | `c2...estimate_emissions`, `c3...store_trip` |
| 9 | UC.1.9 Update Trends and Compare Baseline | C.0 (C.2, C.3) | `c2...compare_baseline`, `c3...update_trends` |
| 10 | UC.1.10 Evaluate Feasible Alternatives | C.0 (C.2) | `c2...evaluate_alternatives` |
| 11 | UC.1.11 Display Commute Result | C.1 and C.4 | `c4...explain_result`, `c1...display_commute_result` -> **Commute Impact Result** |
| 12 | UC.1.12 Review Result | X.1 Commuter | `x1_commuter_sim.review_result` |

Every function carries `@realizes("UC.1.x")` (see `src/model_trace.py`); `tests/test_model_linkage.py` fails if a UC.1 action has no code or if code claims an action that is not in the model.

## Real vs stubbed

| Participant | Real | Stubbed / simplified | Why |
|---|---|---|---|
| X.1 Commuter | - | Scripted simulation | External actor |
| C.1 Web Front End | Field list, result content | No HTML/web layer; plain text output | Walking skeleton, stubs acceptable |
| C.2 Application Service | Distance x factor, always-drive baseline, rule `<3 km and no rain -> walk/bike` with infeasible-mode exclusion | Occupancy not handled; rule threshold still "to validate" (BMA 7.8) | Logic is deterministic and reviewed, so it is real |
| C.3 Data Adapter | - | Placeholder factor table (not reviewed), in-memory trip list, trends without date windows | No factor review or database yet |
| C.4 Explanation Model | Contract: receives only calculated values (needs 1.1.8 / req 2.1.10) | Sentence template instead of a language model | BMA 7.9: no live model call at this stage |
| X.3 Open-Meteo | - | Fixed dry forecast, no HTTP | No real source access yet |

## Deliberately excluded (BMA Section 7.9)

Real source access, live language-model calls, retries, exception handling and runtime logging. Off-nominal behavior (weather outage, invalid input) is not modeled yet either (see docs/traceability.md, open items).

## Demo script (Milestone 1 station, about 2 minutes)

1. SoI in one sentence: EcoCommute lets a commuter log a trip and get its estimated CO2e, a fair always-drive comparison and a feasible greener option.
2. `python -m src.main` - show the output.
3. Trace one need live: need 1.1.4 "Get advice I can use" -> requirement 2.1.4 / 2.1.5 in [SPEC.md](../SPEC.md) -> actions UC.1.6, UC.1.7, UC.1.10 in the model -> `evaluate_alternatives` in `src/c2_application_service/service.py` -> test `test_infeasible_mode_is_never_recommended`.
