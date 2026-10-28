# ADR 0008: Carpool share, a choice of bus routes, and faster place suggestions

Status: **Proposed - needs team review and merge approval** (date: 2026-10-28). Extends [ADR 0006](0006-student-defaults-and-vehicles.md) and [ADR 0007](0007-tcat-gtfs-bus-data.md).

## Context

Three things the team asked for after trying the page: several bus routes can link the same two places and the student should pick one; driving can be shared, so the drive card should offer "alone" or a carpool with a number of people; and the suggestion list under the From and To boxes was slow.

## Decision

**Carpool.** The drive card has "Alone" or "Carpool" and a number of people, you included (2 to 8). A carpool is recorded as the way `carpool` with that number of people. Each person's emissions are the drive emissions over the people in the car (rounded), and the difference is against driving alone. The first design in the code table gave a carpool a fixed factor; it is not used by the page any more. A drive and a carpool of the same trip on the same day count as one car trip, so the same drive cannot be counted twice.

**Bus routes.** The planner returns the best ride of each route that links the places (the one that arrives first), earliest arrival first, at most 5, and only routes that arrive within an hour of the best one, so a night-only route is not offered to someone leaving at 09:15. The page shows the best one in the bus card and lists the others as a pick; picking switches the card and thickens that route on the map (the others stay as thin faint lines). The pick is sent with the choice and recorded with the trip (`bus 10`). An unknown route falls back to the best.

**Faster suggestions.**
- A list appears at once from sample places and answers already known, then the online answer replaces it a moment after the last key (150 ms); stale requests are cancelled.
- The online search starts at 3 characters.
- Connections to the service are kept open and shared by all threads (the development server runs each request in its own thread), and opened ahead of time at start-up.
- Answers for a longer text reuse what is known for its start.
- Places within 25 km of campus were asked for first and the whole world only if nothing was found there. **Changed on 2026-10-28 at the team's request:** the service area is Ithaca and its surroundings, a 40 km circle around campus, and nothing outside it is searched.
- A "quota exceeded" or "too many requests" answer pauses that service for a minute instead of failing every keystroke. Autocomplete and search have **separate quotas**, so when autocomplete is used up, the search service answers instead. Routes are paused separately.

## Consequences

- Measured against the real service: the first suggestion row appears in about 30 ms and the online list in 0.4 s (before: 0.22 s of waiting plus 0.4 to 3.5 s per request). A second set of routes takes about 0.14 s instead of 0.45 s.
- On 2026-10-28 the team key's **autocomplete quota was used up** (HTTP 403 "Quota exceeded", still so after 70 s, so a daily quota; search still worked). The page keeps giving suggestions through the search service. The free quotas are shown on the HeiGIT dashboard.
- The carpool people-count range (2 to 8), the one-hour option window, the 25 km radius and the 150 ms delay are project assumptions.
- A carpool's occupants are not verified; like every trip it is the Commuter's own report.
- An `Accept: application/json` header made the GeoJSON route service answer "406 Not Acceptable", so none is sent; mocked tests could not catch this, a test against a local server does.
- The model (Innoslate) and SPEC.md do not describe the carpool share or the choice of routes.

## Evidence that would change this decision

- A reviewed per-passenger bus factor, or a car occupancy source, replaces the shares.
- Transfers are planned: a route "choice" would then be a whole itinerary.
- A paid or larger quota, or self-hosted geocoding, removes the need for the pause and fallback.
