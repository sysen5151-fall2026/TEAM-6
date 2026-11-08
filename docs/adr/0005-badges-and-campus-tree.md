# ADR 0005: Rule-based badges and a campus tree goal

Status: **Proposed - needs team review and merge approval** (date: 2026-10-27).

## Context

The team wants the product to be more engaging without a leaderboard that rewards people who simply live closer or have more options. Rewards must be explainable and reproducible, and the claims must stay within what the system can show: an estimated difference from a declared baseline, not verified avoided emissions.

## Decision

- A trip counts only after the Commuter confirms it ("I took this" on the compare page). C.2 recomputes distance and emissions from the places and mode; nothing numeric is taken from the browser.
- Eight badges are pure functions of the confirmed trips (`src/c2_application_service/achievements.py`), each shown with its condition and progress: First Step, Green Starter (1 kg estimated difference), Five Day Flow (low-carbon trips on 4 different days in one week), Campus Explorer (5 places), Plan Keeper (took the recommended mode 5 times), Car-Free Week (3 or more trips and no driving in a week), Consistency Champion (4 weeks in a row), Tree Planter (shared).
- Campus tree: everyone's estimated differences add up; each 22 kg reaches one tree. The wording is "a tree gets planted", never "offset".
- Anti-gaming before counting: the same date, places and mode count once; at most 2 trips per date; a trip over 50 km counts as 50 km; trips dated in the future are refused.
- The campus share (126 trips, 41 students, 14.3 kg) is labelled sample data. "Load sample trips" adds invented records for a demonstration and says so.

## Reasons

- Deterministic and testable at the boundaries (every threshold has a test).
- No ranking of individuals; badges reward actions, not circumstances.
- Plan Keeper links the recommendation to what the Commuter actually did.

## Consequences

- All thresholds, the 22 kg per tree and the caps are project assumptions in named constants; the 22 kg needs a cited source before it is presented as fact. Whether anyone actually plants a tree is outside the system.
- Green Starter favours long commutes because it uses the estimated difference; a trip-count version is the alternative.
- Trips live in memory for one demo Commuter and reset on restart. The "Log a trip" page records separately and does not feed badges.
- Per-user identity, persistence and anonymous aggregation with a minimum group size are not built; the campus total is seed plus one Commuter.
- The Innoslate model and `@realizes` tags are not updated.

## Evidence that would change this decision

- Pilot users see the badges as unfair or too easy to earn without effort.
- A cited per-tree figure or an agreed planting partner changes the 22 kg.
