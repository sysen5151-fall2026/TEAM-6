# Route table: entry points to use cases (endpoint-to-use-case audit)

Every route, command and user-triggered entry point of the product, mapped to the use case it serves in Innoslate model 11.3 (`docs/model/EcoCommute_11.3_C8-C9_physical_architecture.xml`). Enumerated from `add_url_rule` calls in `src/c1_web_front_end/` and the `__main__` modules in `src/` on 2026-11-09. The mapping is a draft for the team to confirm (the manual keeps this judgment with the team); items marked **OPEN** need a team decision.

## Entry point serving the selected function F.2.2

| Entry point | Use case | How F.2.2 takes part |
|---|---|---|
| `GET/POST /` and `/compare` (`web_app.plan_page`) | UC.3 Plan and Choose a Trip: UC.3.5 Compare Modes and Recommend, UC.3.6 Present Comparison | The factor for every mode comes from F.2.2.2 (`select_emission_factor`, used by `comparison.compare_modes`); the weather for the recommendation goes through F.2.2.4 (`resolve_trip_forecast`, used by `plan.plan_commute`). |
| `python -m src.main` (`main.py`) | UC.1 Review Commute Impact and Feasible Alternative | UC.1.5 retrieves the factor and UC.1.6/1.7 the forecast through the Data Adapter (C.3) and the X.3 stub. |
| `GET /places` (`web_app.places_api`) | UC.3.14 Suggest Places | Place suggestion is allocated to F.2.2 (system requirement 3.3.1.17) but is not yet a second-level function; planned as F.2.2.5. |

## All web routes

| Route | Handler | Use case |
|---|---|---|
| `/` , `/compare` GET/POST | `plan_page` | UC.3.1 Open Trip Planner, UC.3.2 Enter Start and Destination, UC.3.5, UC.3.6, UC.3.12 Select Vehicles and Ride Sharing |
| `/places` | `places_api` | UC.3.14 Suggest Places |
| `/route-lines` | `route_lines_api` | UC.3.3 Request Routes, UC.3.6 Present Comparison (draws the lines) |
| `/confirm` POST | `confirm_page` | UC.3.7 Choose Way, UC.3.8 Record Trip and Update Progress |
| `/done/<index>` | `done_page` | UC.3.9 Display Trip Result and Badges |
| `/achievements` | `achievements_page` | UC.3.10 Present Progress Pages, UC.3.11 Review Progress |
| `/garden` | `garden_page` | UC.3.10 Present Progress Pages |
| `/login` GET/POST | `auth.login_page` | UC.4.1 Open Log-in Page, UC.4.2, UC.4.3 |
| `/register` GET/POST | `auth.register_page` | UC.4.2 Enter Account Details, UC.4.3 Verify Invite Code and Credentials, UC.4.4 |
| `/account` GET/POST | `auth.account_page` | UC.4.5 Present Signed-in Pages (change password, delete account) |
| `/account/export` | `auth.export_page` | UC.4.5 (the model has no separate "download my data" action: **OPEN**, add one or fold into UC.4.5) |
| `/logout` POST | `auth.logout_page` | UC.4.5 (no separate log-out action in the model: **OPEN**, same decision) |
| `/demo` POST | `web_app.demo_page` | **ORPHAN.** Loads labelled sample trips so a demonstration shows badges and the tree. Traces to no use case. |
| `/reset` POST | `web_app.reset_page` | **ORPHAN.** Clears the signed-in account's trips. Traces to no use case (closest: deletion requirement 2.3.x, outside UC.3). |

## Commands

| Command | Use case |
|---|---|
| `python -m src.main` | UC.1 (command-line walking skeleton, X.1 simulated) |
| `python -m src.main_web` | Starts the web entry for UC.3 and UC.4; hosting by X.5 (operation, OP.x) |
| `python -m src.manage ...` | Invite codes and accounts for UC.4 (invites, users, seed, backup); operation of the pilot (F.2.0), not a Commuter use case |
| `python -m src.update_transit` | Imports the TCAT schedule published by X.7 for UC.3.13 Plan Bus Ride (UC.3.15 is the agency's step) |

## Reconciliation

- **Orphans: 2** (`/demo`, `/reset`). Disposition **OPEN**: either add a use case for "try the product with sample data / clear my trips" to the model and justify it, or delete the routes. Both are guarded by login and the sample data is labelled; neither sends data outside the account.
- **Entry points with an open mapping: 2** (`/account/export`, `/logout`): the model's UC.4.5 covers them only loosely.
- **Use cases with no entry point:**
  - UC.2 Provide Approved Aggregate Summary: planned (Reporting Subsystem C.0.7 is not implemented).
  - UC.1 has no web entry point; its command-line entry is the only one (the web form was removed, see README).
  - UC.3.4 Return Routes, UC.3.15 Publish Bus Schedule and UC.1.1/1.3/1.12 are steps of external actors, so no code claims them.
- Counts: 15 web routes (10 in `web_app.py`, 5 in `auth.py`; `/compare` is an alias of `/`), 4 commands.
