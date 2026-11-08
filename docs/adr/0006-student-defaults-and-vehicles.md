# ADR 0006: Student defaults, owned vehicles, and a reserved bus card

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27). Replaces the "limits" part of [ADR 0004](0004-feasibility-filter-and-recommendation.md). The reserved bus card is replaced by [ADR 0007](0007-tcat-gtfs-bus-data.md).

## Context

The first plan page asked for three settings that did not match how a student plans a trip: ways they could not do (walk, bike), the most extra minutes they would accept over the fastest way, and a door-to-door bus time typed in by hand. The primary user is a university student who is assumed to have no bike. The team also wants a bus option later, from real data.

## Decision

- **Default student.** Drive and walk are always compared. A bike or a scooter is compared only when the Commuter ticks "I have a bike" or "I have a scooter" under **What I have with me**. The ticks are remembered in the browser (`localStorage`), not on the server.
- **Removed from the page:** ways I can't do, most extra minutes, and the typed bus time. `recommend_mode` still accepts `not_feasible` (SRD 2.1.5); the page no longer sets it.
- **Rules that replace the extra-minutes limit** (project assumptions): a walk over 30 min, or a bike or scooter ride over 45 min, is ruled out; rain rules out walk, bike and scooter; ice (0 C or below) and strong wind (40 km/h or more) rule out bike and scooter.
- **Choice:** the lowest estimated CO2e among what is left. Ties go by priority: walk, bike, scooter, bus, carpool, drive. If only driving is left, the reason says driving is the fallback.
- **Scooter.** ORS has no scooter profile, so the scooter is assumed to take the bike route at the bike's speed. Its emission factor (20 g CO2e per km, an electric scooter) is a placeholder like the others.
- **Bus.** A "Coming soon" card is shown and cannot be chosen. The bus is not compared or recommended until real bus data is connected. The factor table keeps its placeholder bus value for later.
- **Date.** The trip date is asked next to the ways ("Date of this trip"), not in the plan form, because it is only used when a way is chosen.

## Consequences

- **SPEC.md requirement 2.1.11 and model 10.9 still say the bus is shown "when the Commuter enters a door-to-door time".** The code no longer does that. The team should update the requirement, the model and the related trace in Innoslate; this ADR does not change them.
- Tests that assumed a bike by default now tick it explicitly.
- Badges count the scooter as a lower-carbon way. Sample (demo) trips are unchanged.
- The command-line UC.1 path and its tests are unchanged.

## Evidence that would change this decision

- Real bus data becomes available: the bus card becomes a compared option.
- A reviewed scooter factor, or an ORS profile for scooters, replaces the assumptions.
- Pilot students want a time-limit control back, or the 30 and 45 minute limits prove wrong.
