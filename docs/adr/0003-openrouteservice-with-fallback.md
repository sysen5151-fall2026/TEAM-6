# ADR 0003: OpenRouteService for places and routes, with an offline fallback

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27).

## Context

Trip distance was typed in by hand. The same two places give different distances by car, on foot and by bike, so one typed number misstates emissions for at least two of the modes. The team wants start and destination in, and per-mode distance and time out, at no cost and without a demonstration that can break when a network call fails.

## Decision

Add a route adapter to C.3 (`src/c3_data_adapter/route_adapter.py`) that calls OpenRouteService (ORS): the geocoder for place text and the Directions service for the `driving-car`, `foot-walking` and `cycling-regular` profiles. C.2 `compare_modes` multiplies each mode's own distance by its factor and measures the difference against the drive route's distance.

- The key is read from the environment variable `ORS_API_KEY` and is never stored in the repository or sent to the browser.
- With no key, or when a call fails or returns an unexpected shape, each mode falls back individually to an estimate (straight line x a detour factor, fixed speeds) built from a short list of sample places. The page labels the source of every row.
- Transit is not routed. It will be entered by the Commuter (later step).

## Reasons

- Free tier and no card on file (to be confirmed at sign-up); community and non-profit plans exist.
- The fallback keeps the demonstration working without a key, offline, or over quota.
- Only C.3 knows the service; replacing ORS changes one module.

## Consequences

- **Checked live once (2026-10-27)** with a free key: place search and the three profiles returned the expected shapes, and the three modes gave different distances for the same two places. Automated tests use mocked responses only.
- ORS announced a move from `api.openrouteservice.org` to `api.heigit.org`; the same paths returned 404 on the new host, so the old host is the default and `ORS_BASE_URL` overrides it. Re-check before the final demonstration.
- The fallback detour factors and speeds are assumptions, not measurements.
- The route service is a new external system and C.3 gains a new responsibility. The model (Innoslate) and its numbering have not been updated; the team decides the identifiers.
- Distances are one-way and per mode; emission factors are still placeholders.

## Evidence that would change this decision

- The free quota or terms no longer fit the pilot.
- A live call shows a response shape or limit that this adapter does not handle.
