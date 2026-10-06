# EcoCommute (TEAM-6) - SYSEN 5151

## Operational Concept (OpsCon)

A student or employee opens EcoCommute to record a commute. The application presents fields for mode, distance, date, occupancy when applicable and user-selected feasibility settings. The commuter submits the trip. EcoCommute accepts the entry and retrieves an applicable reviewed emission factor from its internal store. It requests weather for the approved coarse location and trip time and receives the forecast. It estimates trip CO2e, stores the record, updates weekly and monthly trends and compares the trip with a stated always-drive baseline. It evaluates transparent rules using distance, weather and the commuter's settings and displays the impact, trend, baseline difference and explanation of a feasible alternative. The commuter reviews the result and retains the choice of future travel mode.

The nominal scenario assumes an existing account and consent, valid supported inputs, suitable stored factors and an available forecast. Factor ingestion happens before this scenario. Institutional reporting is a separate operating scenario subject to access and aggregation rules. The commuter receives decision support rather than a guarantee of route safety or actual emission reduction.

*(Source: Team 6 Business or Mission Analysis, Section 7.1, copied without paraphrase.)*

## System of Interest and external systems

- **SoI:** C.0 EcoCommute, a responsive web application that estimates commute CO2e and suggests feasible greener options (mission: help commuters interpret impact and consider practical lower-carbon options, and give institutions approved engagement information).
- **External:** X.1 Commuter, X.2 Pilot Administrator, X.3 Open-Meteo, X.4 Emission Factor Publisher, X.5 Hosting Provider.
- **Inside C.0:** C.1 Web Front End, C.2 Application Service, C.3 Data Adapter, C.4 Explanation Model.
- Interface inventory and boundary: [docs/context.md](docs/context.md).

## Where things are

| Path | What it is |
|---|---|
| [SPEC.md](SPEC.md) | Stakeholder requirements (27, from the SRD) with acceptance criteria and model links |
| [docs/context.md](docs/context.md) | Boundary, interface inventory, component-to-directory map |
| [docs/walking-skeleton.md](docs/walking-skeleton.md) | UC.1 call order; what is real vs stubbed |
| [docs/traceability.md](docs/traceability.md) | Need -> requirement -> UC.1 action -> code -> test |
| [docs/environment.md](docs/environment.md), [docs/adr/](docs/adr/) | Toolchain and decisions |
| [docs/prompt-log.md](docs/prompt-log.md) | GenAI provenance log (required by the course) |
| `src/c1_web_front_end` ... `src/c4_explanation_model` | Internal assets C.1-C.4 |
| `src/x1_commuter_sim`, `src/x3_open_meteo_stub` | Simulated external actor X.1 and stubbed external system X.3 |
| `tests/` | UC.1 end-to-end tests and the model-linkage check |

## Run the walking skeleton

Python 3.12, standard library only (no installs).

```powershell
git clone https://github.com/sysen5151-fall2026/TEAM-6.git
cd TEAM-6
python -m src.main
python -m unittest discover -s tests -t .
```

`python -m src.main` runs UC.1 once, end to end, with stubs. Do not run `python src/main.py` (package imports need `-m`).

**Status (Milestone 1):** one stubbed end-to-end path for UC.1; emission factors are placeholders, there is no web UI, no persistence, no real weather call and no language model yet. See [docs/walking-skeleton.md](docs/walking-skeleton.md).

## Team

- Luyu Chen - Project Manager and Integration Lead
- Mingjie Fang - Quality, Risk and Documentation Lead
- Karen Li - Product and Stakeholder Lead
- Yinping Yin - Sustainability Data and Analysis Lead
- Yiyang Zou - Technical Architecture Lead

## Workflow

- `git pull`
- `git switch -c feat/your-feature-name` (create a branch)
- change files and save
- `git add .`
- `git commit -m "Describe your change"`
- `git push -u origin feat/your-feature-name`
- open a pull request, review and merge on GitHub
- `git switch main` then `git pull origin main`
- `git branch -d feat/your-feature-name`
- Any GenAI-assisted change is recorded in [docs/prompt-log.md](docs/prompt-log.md).
