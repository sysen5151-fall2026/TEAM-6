# EcoCommute (TEAM-6) - SYSEN 5151

**Project home page: <https://sysen5151-fall2026.github.io/TEAM-6/>**

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
| [Project home page](https://sysen5151-fall2026.github.io/TEAM-6/) ([source](docs/index.html)) | Live site with an interactive commute demo, UC.1 walkthrough and traceability explorer (GitHub Pages, served from `/docs`) |
| [SPEC.md](SPEC.md) | Stakeholder requirements (33: 27 from the SRD, 2.1.10, and five web-flow drafts 2.1.11-2.1.14 and 2.2.5) with acceptance criteria and model links |
| [docs/context.md](docs/context.md) | Boundary, interface inventory, component-to-directory map |
| [docs/walking-skeleton.md](docs/walking-skeleton.md) | UC.1 call order; what is real vs stubbed |
| [docs/traceability.md](docs/traceability.md) | Need -> requirement -> UC.1 action -> code -> test |
| [docs/environment.md](docs/environment.md), [docs/adr/](docs/adr/) | Toolchain and decisions |
| [docs/ch6-ch7/](docs/ch6-ch7/) | Chapter 6 and 7 report (Architecture Definition: Function: UC.1 trace, first-level IDEF0, hierarchy, N2, requirements traceability) as `.docx` and `.pdf`, its Innoslate figures and the scripts that build it (`scripts/`) |
| [docs/model/](docs/model/) | Innoslate exports: 10.6, 10.7 (and the 24 Oct 2026 re-export), 10.8 (10.7 plus the two trace edits, restored risk links) and 10.9 (10.8 plus the web-flow needs, requirements, route service, UC.3 and risks; [changes](docs/model/10.9-changes.md); imported into Innoslate, Intelligence 81% with no errors) |
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

## Run the web entry

Needs Flask (see [ADR 0002](docs/adr/0002-flask-web-entry.md)); the commands above need nothing installed.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m src.main_web
```

Then open <http://127.0.0.1:5000>. Emission factors are still placeholders and trips are kept in memory only.

The pages: **Plan** (start and destination are required; every way is compared and one is recommended; you then choose the way you took), a **done** page after choosing (estimated saving, campus tree progress, and a popup for any new badge), **Garden** (an animated campus garden with one tree per reached goal) and **Achievements** (your trip history, earned badges and badges still to go). The earlier "log a trip with a typed distance" web form was removed; the command-line UC.1 path (`python -m src.main`) is unchanged.

The **Plan** page shows drive and walk (and bike or scooter when ticked) distance, time and CO2e between two places ([ADR 0003](docs/adr/0003-openrouteservice-with-fallback.md)). To use OpenRouteService, get a free key from openrouteservice.org and set it before starting the server; without it the page uses a labelled estimate between sample places (Cornell Arts Quad, Collegetown, Ithaca Commons, Cornell Gates Hall, Upson Hall, Duffield Hall, Olin Library, Willard Straight Hall). The From and To boxes work like a map search: type, pick a place from the list, and a map shows it (the page says whether place search is live; it needs `ORS_API_KEY`). If a server is already running on port 5000, stop it first or you will see its older page. The map opens on your current location when the browser allows it (your position stays in the browser until you press *Start from my location*), drops a pin for the start and a flag for the destination, and draws the drive (thick orange), bike (dashed blue) and walk (dotted green) routes together with their distance and time. Without a routing answer the lines are dashed straight-line estimates and say so. The live service was checked once on 2026-10-27; ORS plans to move to `api.heigit.org`, so set `ORS_BASE_URL` if the old host stops working.

The same page recommends one mode ([ADR 0004](docs/adr/0004-feasibility-filter-and-recommendation.md)): it rules out ways using current weather at the start (Open-Meteo, no key) and a time limit (walk 30 min, bike or scooter 45 min), then picks the lowest estimated CO2e among what is left and says why; ties go to walk, then bike, then scooter ([ADR 0006](docs/adr/0006-student-defaults-and-vehicles.md)). A student is assumed to have no bike: under **What I have with me** you tick a bike or a scooter (remembered in your browser) to compare them. **Start from my location** sits under the From box. The bus is a "Coming soon" card until bus data is connected; there is no transit routing.

**Bus (TCAT).** The bus comes from TCAT's published GTFS schedule ([ADR 0007](docs/adr/0007-tcat-gtfs-bus-data.md)). Build the local index once (and again when TCAT publishes a new schedule; the current one runs to 2026-12-19):

```powershell
.venv\Scripts\python -m src.update_transit
```

It downloads the feed (about 1.5 MB), checks it and writes `data/tcat/tcat.sqlite` (git ignores `data/`: the feed's terms for redistribution were not found, so each machine builds its own). The server prints whether the schedule was found. The **Leaving** date and time decides which services run (weekday, weekend, holiday exceptions) and which bus is next; the bus card shows the real route, stops, times and when to leave, and the map draws the ride. Direct rides only; times are the timetable, not live positions. Without the index the bus card says so.

Choose a way with **Choose this way** and the **Achievements** and **Garden** pages ([ADR 0005](docs/adr/0005-badges-and-campus-tree.md)) shows eight rule-based badges with their conditions and a campus tree goal (22 kg estimated difference per tree, a project assumption). **Load sample trips** adds invented records for a demonstration; the campus share is sample data and is labelled on the page.

```powershell
$env:ORS_API_KEY = "your-key"
.venv\Scripts\python -m src.main_web
```

The server looks for the key in this order and prints which one it used when it starts: the process environment, a `.env` file in the project folder (one line `ORS_API_KEY=your-key`; git ignores it), then the Windows user environment variable. A variable saved after a terminal was opened is not visible to that terminal, which is why the last two exist. The page itself says whether place search is live.

**Status (Milestone 1):** one stubbed end-to-end path for UC.1; emission factors are placeholders, the web UI is a single minimal page (see below), there is no persistence, no real weather call and no language model yet. See [docs/walking-skeleton.md](docs/walking-skeleton.md).

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
