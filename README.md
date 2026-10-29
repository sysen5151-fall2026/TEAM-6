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
| [Project home page](https://sysen5151-fall2026.github.io/TEAM-6/) ([source](docs/index.html)) | Product home page (features, in-page planner demo, FAQ) plus an [About the project](docs/project.html) page (architecture, traceability, status, roadmap, documents, team); GitHub Pages, served from `/docs` |
| [SPEC.md](SPEC.md) | Stakeholder requirements (33: 27 from the SRD, 2.1.10, and five web-flow drafts 2.1.11-2.1.14 and 2.2.5) with acceptance criteria and model links |
| [docs/context.md](docs/context.md) | Boundary, interface inventory, component-to-directory map |
| [docs/walking-skeleton.md](docs/walking-skeleton.md) | UC.1 call order; what is real vs stubbed |
| [docs/traceability.md](docs/traceability.md) | Need -> requirement -> UC.1 action -> code -> test |
| [docs/environment.md](docs/environment.md), [docs/adr/](docs/adr/) | Toolchain and decisions |
| [docs/ch4-ch5/](docs/ch4-ch5/) | Chapter 4 and 5 report (System Requirements Definition) as `.docx` and its Innoslate figures |
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

Then open <http://127.0.0.1:5000>. Everything needs an account (next section). Emission factors are still placeholders.

The pages: **Plan** (start and destination are required; every way is compared and one is recommended; you then choose the way you took), a **done** page after choosing (estimated saving, campus tree progress, and a popup for any new badge), **Garden** (an animated campus garden with one tree per reached goal) and **Achievements** (your trip history, earned badges and badges still to go). The earlier "log a trip with a typed distance" web form was removed; the command-line UC.1 path (`python -m src.main`) is unchanged.

The **Plan** page shows drive and walk (and bike or scooter when ticked) distance, time and CO2e between two places ([ADR 0003](docs/adr/0003-openrouteservice-with-fallback.md)). To use OpenRouteService, get a free key from openrouteservice.org and set it before starting the server; without it the page uses a labelled estimate between sample places (Cornell Arts Quad, Collegetown, Ithaca Commons, Cornell Gates Hall, Upson Hall, Duffield Hall, Olin Library, Willard Straight Hall). The From and To boxes work like a map search: type, pick a place from the list, and a map shows it (the page says whether place search is live; it needs `ORS_API_KEY`). If a server is already running on port 5000, stop it first or you will see its older page. The map opens on your current location when the browser allows it (your position stays in the browser until you press *Start from my location*), drops a pin for the start and a flag for the destination, and draws the drive (thick orange), bike (dashed blue) and walk (dotted green) routes together with their distance and time. Without a routing answer the lines are dashed straight-line estimates and say so. The live service was checked once on 2026-10-27; ORS plans to move to `api.heigit.org`, so set `ORS_BASE_URL` if the old host stops working.

The same page recommends one mode ([ADR 0004](docs/adr/0004-feasibility-filter-and-recommendation.md)): it rules out ways using current weather at the start (Open-Meteo, no key) and a time limit (walk 30 min, bike or scooter 45 min), then picks the lowest estimated CO2e among what is left and says why; ties go to walk, then bike, then scooter ([ADR 0006](docs/adr/0006-student-defaults-and-vehicles.md)). A student is assumed to have no bike: under **What I have with me** you tick a bike or a scooter (remembered in your browser) to compare them. **Start from my location** sits under the From box. The bus is a "Coming soon" card until bus data is connected; there is no transit routing.

**Bus (TCAT).** The bus comes from TCAT's published GTFS schedule ([ADR 0007](docs/adr/0007-tcat-gtfs-bus-data.md)). Build the local index once (and again when TCAT publishes a new schedule; the current one runs to 2026-12-19):

```powershell
.venv\Scripts\python -m src.update_transit
```

It downloads the feed (about 1.5 MB), checks it and writes `data/tcat/tcat.sqlite` (git ignores `data/`: the feed's terms for redistribution were not found, so each machine builds its own). The server prints whether the schedule was found. The **Leaving** date and time decides which services run (weekday, weekend, holiday exceptions) and which bus is next; the bus card shows the real route, stops, times and when to leave, and the map draws the ride. Direct rides only; times are the timetable, not live positions. Without the index the bus card says so. When several routes link the two places the card lists them (best arrival first, up to 5) and you pick one; the map shows the picked route thick and the others faint, and the trip is recorded with the route ([ADR 0008](docs/adr/0008-carpool-bus-choice-and-faster-suggestions.md)).

**Drive: alone or carpool.** The drive card asks who is in the car. A carpool with 2 to 8 people (you included) shares the car's emissions between them, so each person's CO2e is the drive emissions divided by the people; the saving is against driving alone.

**Place suggestions** show from sample places at once and are completed online a moment later. OpenRouteService's free plan has daily quotas that differ per service; when the autocomplete quota is used up the page uses the search service instead, and when both are used up it shows sample places and says so for a minute before trying again. The dashboard at HeiGIT shows what is left.

Choose a way with **Choose this way** and the **Achievements** and **Garden** pages ([ADR 0005](docs/adr/0005-badges-and-campus-tree.md)) shows eight rule-based badges with their conditions and a campus tree goal (22 kg estimated difference per tree, a project assumption). **Load sample trips** adds invented records for a demonstration; the campus share is sample data and is labelled on the page.

```powershell
$env:ORS_API_KEY = "your-key"
.venv\Scripts\python -m src.main_web
```

The server looks for the key in this order and prints which one it used when it starts: the process environment, a `.env` file in the project folder (one line `ORS_API_KEY=your-key`; git ignores it), then the Windows user environment variable. A variable saved after a terminal was opened is not visible to that terminal, which is why the last two exist. The page itself says whether place search is live.

**Status:** two paths run today. The command-line UC.1 walking skeleton (`python -m src.main`) is still one stubbed end-to-end path. The Flask web app adds invite-only accounts, saved trips (SQLite), the Plan, Done, Garden and Achievements pages with real route (OpenRouteService), weather (Open-Meteo) and TCAT bus data, a feasibility-based recommendation, carpool, badges and the campus tree. Still open: reviewed emission factors (placeholders today), a language-model explanation, and the pilot usability measurements. 386 automated tests pass (those needing Flask or a built bus index are skipped when it is missing). See [docs/walking-skeleton.md](docs/walking-skeleton.md) and the [project home page](https://sysen5151-fall2026.github.io/TEAM-6/).

## Accounts and invites

The site is for a small invited group (the team, the professor and the TA), not the public ([ADR 0009](docs/adr/0009-accounts-invites-and-persistence.md)). Accounts, trips and the place and route cache live in one file, `data/app.sqlite`, so everything is still there after the server stops. `data/` is git-ignored: **keep it private and back it up.**

Make invite codes and demo accounts on the computer that runs the site:

```powershell
.venv\Scripts\python -m src.manage create-invite --label "Karen"
.venv\Scripts\python -m src.manage create-user professor --generate --with-sample-trips
.venv\Scripts\python -m src.manage users
.venv\Scripts\python -m src.manage invites
.venv\Scripts\python -m src.manage backup
```

- **The simple way (what the team uses):** write `data/roster.json` (git-ignored, so it never reaches GitHub) and run `python -m src.manage seed`. The file lists the accounts (user name, password) and **three shared invite codes** (team members, Luyu, the professor), for example `{"invites": [{"label": "team", "code": "ECO-TEAM-XXXX"}], "users": [{"username": "karen", "password": "pass#one"}, {"username": "test01", "password": "111111", "sample_trips": true}]}`. Running it again changes nothing that already exists.
- A person with a code opens the site, chooses **Create an account**, and fills in user name, password, password again and the invite code (no email). A shared code works for many accounts and never expires; the sign-up form has no daily limit because the site is private.
- `create-invite` makes one more random code, printed **once** and stored only as a hash. `create-user ... --generate` makes an account without an invite and prints a random password once; `--with-sample-trips` fills it with labelled sample trips, so a demo shows badges and the tree at once.
- Other commands: `revoke-invite ID`, `set-password NAME` (signs that account out everywhere), `delete-user NAME`, `cache-stats`, `clear-cache`. Run `python -m src.manage --help`.
- Passwords (at least 6 characters) are stored as salted scrypt hashes, never in the clear. Five wrong passwords lock a user name for 15 minutes. `data/roster.json` itself holds the passwords in plain text: keep it on your computer only and delete it after seeding if you prefer.
- Each account sees only its own trips. The shared tree adds every account's trips (and the labelled sample data) and shows only the total. On the **My account** page a person can change their password, download their data or delete the account.
- Online place search and routes need a signed-in account, which keeps the free quota for invited people. Places looked up once are kept, so they are not looked up again for months.

### Using it from other computers

By default the site listens on this computer only. For teammates on other computers, while it runs on yours, in order of preference:

1. **A private network (Tailscale).** Everyone installs Tailscale and joins your network; they open `http://<your Tailscale address>:5000`. Start with `python -m src.main_web --host 0.0.0.0`. The traffic is encrypted by Tailscale and nothing is opened to the internet. (Not tested here.)
2. **An https tunnel** (for example Cloudflare's `cloudflared`). It gives a public https address; only invite holders can make accounts, but anyone can open the log-in page. Set `ECOCOMMUTE_BEHIND_PROXY=1` and `ECOCOMMUTE_SECURE_COOKIES=1` before starting. Free tunnels usually change address each time. (Not tested here.)
3. **Your phone's hotspot** (tested on 2026-10-28 with an iPhone hotspot and the same iPhone's browser; steps below).
4. **The same Wi-Fi.** `--host 0.0.0.0` and your computer's local address. Pages are not encrypted, so passwords cross the network as plain text; use only a network you trust. Campus Wi-Fi often stops devices from reaching each other.

The demonstration can simply run on your own computer. If the computer is off, the site is off.

#### Step by step: the phone hotspot

1. Turn on the personal hotspot on the phone and connect the computer's Wi-Fi to it. Teammates connect their devices to the same hotspot.
2. On the computer, in the project folder, start the site so that other devices may connect:
   ```powershell
   .venv\Scripts\python -m src.main_web --host 0.0.0.0
   ```
   If Windows asks whether to allow Python through the firewall, allow it on **private** networks.
3. In another PowerShell window run `ipconfig`. Under the **Wireless LAN adapter** (WLAN) that is connected to the hotspot, read the **IPv4 address** (for an iPhone hotspot it looks like `172.20.10.3`; ignore Ethernet, vEthernet, WSL and VMware entries).
4. On the phone or any device on the same hotspot, open `http://<that address>:5000` and log in.
5. The address can change each time the hotspot is switched on, so run `ipconfig` again before each session. If the page does not open, check that both devices are on the same hotspot, that the site is still running, and the firewall prompt in step 2.

What does and does not work over the hotspot:

- Everything works except **"Start from my location" and "Show my location"**. Browsers only share a location with `https` pages (or with the computer itself, at `localhost`), and `http://172.20.10.3:5000` is plain http, so no permission question is ever shown. The page says so and asks the person to type a place. Nothing on the site can change this.
- To use locations on a phone, the site must be reached over `https`: an https tunnel (item 2 above, for example Cloudflare's `cloudflared tunnel --url http://localhost:5000`, with `ECOCOMMUTE_BEHIND_PROXY=1` and `ECOCOMMUTE_SECURE_COOKIES=1` set first) or Tailscale's https. This was **not tested here**.
- Traffic on the hotspot is not encrypted, so passwords cross it as plain text; only the people connected to the hotspot could read them. Route lookups use the phone's mobile data.

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
