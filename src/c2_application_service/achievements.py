"""Badge rules and the campus tree goal.

Every rule is a pure function of the confirmed trips, so the same trips always give
the same badges, and each rule is shown to the Commuter next to its progress.
Numbers here are PROJECT ASSUMPTIONS; the campus share is sample data, labelled as such.
"""

from datetime import date, timedelta

from src.interfaces import BadgeStatus, CampusGoal

LOW_CARBON = ("walk", "bike", "bus", "carpool")

# Anti-gaming limits applied before anything is counted.
MAX_COUNTED_PER_DAY = 2  # trips beyond this on one date are kept but not counted
MAX_TRIP_KM = 50.0  # a longer trip counts as if it were this long

TREE_GOAL_G = 22_000.0  # estimated difference that earns one tree (assumption; cite a source)
CAMPUS_SEED = {"difference_g": 14_300.0, "trips": 126, "students": 41}  # sample data

DAYS_FOR_FLOW = 4
PLACES_FOR_EXPLORER = 5
RECOMMENDED_TRIPS_FOR_KEEPER = 5
TRIPS_FOR_CAR_FREE_WEEK = 3
WEEKS_FOR_CONSISTENCY = 4
GREEN_STARTER_G = 1_000.0


def counted_trips(trips) -> list:
    """Drop repeats of date, places and mode, and keep at most two trips per date."""
    seen, per_day, kept = set(), {}, []
    for t in trips:
        key = (t.date, t.origin, t.destination, t.mode)
        if key in seen or per_day.get(t.date, 0) >= MAX_COUNTED_PER_DAY:
            continue
        seen.add(key)
        per_day[t.date] = per_day.get(t.date, 0) + 1
        kept.append(t)
    return kept


def _counted_difference_g(trip) -> float:
    if trip.distance_km > MAX_TRIP_KM:
        return trip.difference_g * MAX_TRIP_KM / trip.distance_km
    return trip.difference_g


def _week_of(day: str) -> int:
    """Week number counted from the Monday of that date's week (consecutive weeks differ by 1)."""
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).toordinal() // 7


def _longest_run(weeks) -> int:
    best = run = 0
    previous = None
    for w in sorted(set(weeks)):
        run = run + 1 if previous is not None and w == previous + 1 else 1
        best, previous = max(best, run), w
    return best


def campus_goal(trips) -> CampusGoal:
    mine = counted_trips(trips)
    total = CAMPUS_SEED["difference_g"] + sum(max(_counted_difference_g(t), 0) for t in mine)
    return CampusGoal(
        total_g=round(total),
        goal_g=TREE_GOAL_G,
        trees_reached=int(total // TREE_GOAL_G),
        into_next_g=round(total % TREE_GOAL_G),
        trips=CAMPUS_SEED["trips"] + len(mine),
        students=CAMPUS_SEED["students"] + (1 if mine else 0),
        sample_note=f"{CAMPUS_SEED['trips']} trips by {CAMPUS_SEED['students']} students are sample data",
    )


def evaluate_badges(trips) -> tuple:
    mine = counted_trips(trips)
    low = [t for t in mine if t.mode in LOW_CARBON]

    days_by_week = {}
    for t in low:
        days_by_week.setdefault(_week_of(t.date), set()).add(t.date)
    best_days = max((len(d) for d in days_by_week.values()), default=0)

    places = {t.destination for t in low}
    kept_plan = sum(1 for t in mine if t.recommended_mode and t.mode == t.recommended_mode)

    trips_by_week, drive_weeks = {}, set()
    for t in mine:
        w = _week_of(t.date)
        trips_by_week[w] = trips_by_week.get(w, 0) + 1
        if t.mode == "drive":
            drive_weeks.add(w)
    best_free = max((n for w, n in trips_by_week.items() if w not in drive_weeks), default=0)

    run = _longest_run(_week_of(t.date) for t in mine)
    difference_g = sum(max(_counted_difference_g(t), 0) for t in low)
    goal = campus_goal(trips)
    planted = 1 if goal.trees_reached >= 1 and mine else 0

    def badge(id_, name, condition, icon, progress, target, unit):
        return BadgeStatus(id_, name, condition, icon, min(int(progress), target), target, unit, progress >= target)

    return (
        badge("first_step", "First Step", "Confirm your first walk, bike, bus or carpool trip.",
              "walk", len(low), 1, "trip"),
        badge("green_starter", "Green Starter", "Reach 1 kg estimated difference from driving.",
              "leaf", round(difference_g), int(GREEN_STARTER_G), "g"),
        badge("five_day_flow", "Five Day Flow",
              f"Low-carbon trips on {DAYS_FOR_FLOW} different days in one week.",
              "calendar-check", best_days, DAYS_FOR_FLOW, "days"),
        badge("campus_explorer", "Campus Explorer",
              f"Low-carbon trips to {PLACES_FOR_EXPLORER} different places.",
              "map-pin", len(places), PLACES_FOR_EXPLORER, "places"),
        badge("plan_keeper", "Plan Keeper",
              f"Take the recommended mode {RECOMMENDED_TRIPS_FOR_KEEPER} times.",
              "target", kept_plan, RECOMMENDED_TRIPS_FOR_KEEPER, "trips"),
        badge("car_free_week", "Car-Free Week",
              f"A week with {TRIPS_FOR_CAR_FREE_WEEK} or more trips and none by driving.",
              "car-off", best_free, TRIPS_FOR_CAR_FREE_WEEK, "trips"),
        badge("consistency_champion", "Consistency Champion",
              f"Confirm a trip in {WEEKS_FOR_CONSISTENCY} weeks in a row.",
              "flame", run, WEEKS_FOR_CONSISTENCY, "weeks"),
        badge("tree_planter", "Tree Planter",
              "Shared: you logged a trip and the campus reached a tree.",
              "seeding", planted, 1, "tree"),
    )
