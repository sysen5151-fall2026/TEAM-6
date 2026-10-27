# ADR 0004: Feasibility filter, then lowest emission, with a stated reason

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27).

## Context

"Best" for a commute is not the cheapest or the shortest. It depends on whether a mode is realistic today (weather, the Commuter's own limits, extra time) and then on emissions. A single opaque score would be hard to test and hard to explain.

## Decision

`recommend_mode` (C.2) works in three fixed steps:

1. **Rule out** modes that fail a stated rule: marked not feasible by the Commuter; walking or cycling in rain (>= 0.1 mm); cycling at or below 0 C or at or above 40 km/h wind; any mode more than the Commuter's limit of extra minutes (default 10) over the fastest.
2. **Choose** the lowest estimated CO2e among the rest, ties to the faster mode. If nothing remains, choose the fastest mode the Commuter has not ruled out and say so. If every mode is ruled out by the Commuter, recommend none.
3. **Explain** with `explain_recommendation` (C.4), which only restates values already computed. Every ruled-out mode is shown with its reason.

Weather is the current condition at the start place from Open-Meteo (no key). If it cannot be fetched, the page says the weather rules were not applied. The bus is included only when the Commuter types a door-to-door time; its distance is assumed equal to the drive route.

## Reasons

- Deterministic and testable: the same inputs give the same answer, and a mode the Commuter marked not feasible is never recommended (SRD 2.1.5).
- No weights to defend: the order of rules is the whole logic.
- A failed weather call degrades to a disclosed gap, not an error.

## Consequences

- The thresholds are project assumptions, not safety guidance, and are named constants in `recommendation.py`.
- Current conditions are not the forecast for the trip time; using the planned departure is a later step.
- Daylight, elevation, accessibility and a real transit route are not covered.
- The model (Innoslate) is not updated for the new weather use or the recommendation function.

## Evidence that would change this decision

- Pilot users rate recommendations as unrealistic, which would send the thresholds back for review.
- A forecast source or transit data becomes available and affordable.
