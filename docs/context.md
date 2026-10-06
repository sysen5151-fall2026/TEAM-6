# Context: boundary and interface inventory

Source: Team 6 Business or Mission Analysis (BMA) Sections 4.1-4.5 and 7.9; Stakeholder Needs and Requirements report (updated diagrams in its Appendix B). The authoritative model is the Innoslate project (export `EcoCommute 10.4.xml`).

## System of Interest

C.0 EcoCommute includes the web interface, account and consent controls, trip records, reviewed factor store, calculation, trends, baseline comparison, recommendation rules and institutional aggregation. Users and institutional administrators remain external because the team controls the software response, not their travel or program decisions. Weather and factor publication remain external because the team consumes rather than produces those information services. Hosting is an external enabling service supporting application operation.

## Interface inventory

| External asset | Direction and information | Proposed form |
|---|---|---|
| X.1 Commuter | In: mode distance occupancy date coarse area and feasibility settings. Out: estimate trend baseline advice explanation | Web form and result view; internal structured request |
| X.2 Pilot Administrator | In: authorized period and group request. Out: approved aggregate summary | Authenticated dashboard; approved aggregate export |
| X.3 Open-Meteo | Out: approved coarse location and time query. In: forecast and forecast timestamp | HTTPS API; structured response |
| X.4 Emission Factor Publisher | In: published values units geography methodology and version | Reviewed file or source document ingestion; no live UC.1 call |
| X.5 Hosting Provider | Out: release configuration and operational service requests. In: hosting service status | Deployment artifacts and provider interface; no personal data in repository |

## Scope

Included: manual logging, documented CO2e estimates, weekly and monthly views, the always-drive baseline, explainable rules with user feasibility controls, account controls and approved institutional summaries; one controlled pilot. Excluded: native apps, passive GPS, carbon credits, comprehensive transit integrations. Transit or carpool suggestions depend on user-declared feasibility; no live route or timetable certainty is implied.

## Components inside C.0 and where they live

Boundary directories use asset-based names (BMA Section 7.9).

| Asset | Directory | Role in UC.1 | Status |
|---|---|---|---|
| C.1 Web Front End | `src/c1_web_front_end` | Presents entry fields, forwards the request, displays the result | Stub (plain text, no web layer) |
| C.2 Application Service | `src/c2_application_service` | Estimation, always-drive baseline, recommendation rules | Real logic, placeholder factors |
| C.3 Data Adapter | `src/c3_data_adapter` | Factor store, trip store, weather access | Stub (in-memory, hard-coded) |
| C.4 Explanation Model | `src/c4_explanation_model` | Explains an already-calculated result | Stub (hard-coded sentence) |
| X.1 Commuter (external) | `src/x1_commuter_sim` | Scripted simulation that drives UC.1 | Simulation |
| X.3 Open-Meteo (external) | `src/x3_open_meteo_stub` | Returns the forecast | Stub (fixed dry forecast) |

X.2, X.4 and X.5 do not take part in UC.1 and have no code yet.

**Model update:** `docs/model/EcoCommute_10.5_C1-C4.xml` adds the internal assets C.1-C.4 under C.0 (decomposes / decomposed by) and re-points the UC.1 performers: UC.1.2 and UC.1.11 -> C.1; UC.1.5, UC.1.8, UC.1.9, UC.1.10 -> C.2; UC.1.6 -> C.3. C.4 is modeled but performs no action yet (see docs/traceability.md, open item O-1). UC.1.1, 1.3, 1.4, 1.12 stay with X.1; UC.1.7 stays with X.3; OP.1-OP.5 and UC.2 stay with C.0. Import this file into Innoslate so the model matches the code.
