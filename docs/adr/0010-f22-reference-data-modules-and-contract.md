# ADR 0010: F.2.2 gets one module per second-level function, behind a contract

Status: **Proposed - needs team review and merge approval** (date: 2026-11-09).

## Context

Model 11.3 decomposes F.2.2 Manage Reference Data into F.2.2.1 to F.2.2.4, each performed by one module (C.0.2.1 to C.0.2.4). The code kept this work inside the Data Adapter (C.3) and the route/weather adapters, so no module carried a function ID, and no function existed for loading reviewed factors (F.2.2.1) or resolving the forecast for the trip (F.2.2.4). Chapter 4.4 asks for one module per function with the function identifier in its docstring and a signature built from its ICOMs; Chapter 7.4 asks for the internal flows to be written as a contract before the code.

## Decision

- New package `src/c0_2_reference_data/` with `load_emission_factors`, `select_emission_factor`, `request_weather_forecast` and `resolve_trip_forecast`. Inputs are parameters, controls keyword-only, outputs return values (Table 4 of the Chapter 8-9 report).
- `contracts/api-v1.yaml` is written from the F.2.2 flows (IO.23, IO.24 and the six carried-down flows), one operation per function.
- **Timeouts are fixed configuration, not caller data.** The 1.0 s Open-Meteo limit (requirement 5.4.4) is the constant `WEATHER_TIMEOUT_S` and travels in IO.24, not as a field of the request.
- `select_emission_factor` uses the shipped set `published_factors.py` when no factor set is given: EPA GHG Emission Factors Hub, January 2025, Table 10 (passenger car 0.297 kg CO2, 0.0059 g CH4, 0.0053 g N2O per vehicle-mile; bus 0.066, 0.0046, 0.0019 per passenger-mile), converted with the hub's AR5 GWPs (CH4 28, N2O 265) to **185.523 g CO2e/km for drive and 41.403 g/km per passenger for bus**; walk and bike are 0 by assumption. This replaces the placeholders 192 and 105. Tailpipe only. Scooter and carpool are not in the EPA table and keep the labelled C.3 placeholder. **Reviewed by the Method Reviewer, Yinping Yin, on 2026-11-09 (`docs/factor-review.md`).** `comparison.py` and `plan.py` call F.2.2.2 and F.2.2.4. The command-line UC.1 skeleton still uses C.3 directly.
- `request_weather_forecast` (F.2.2.3) builds the query and context but is not yet on the web path: the Plan page reads current weather through `current_weather` in C.3.

Model entities affected: F.2.2.1 to F.2.2.4, C.0.2.1 to C.0.2.4, IO.23, IO.24, requirements 5.4.1 to 5.4.4, 5.5.6, 5.5.7.
