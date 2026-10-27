"""Web pages for C.1.

Flow: plan (start and destination are required, every way is compared) ->
choose a way -> done page (saving, tree progress, new badges) -> garden and
achievements pages to look back. The pages only collect input and show what
C.2 returns; no calculation or rule lives here.

Run:  python -m src.main_web
"""

from datetime import date as _date

from flask import Flask, redirect, render_template, request, url_for

from src.c2_application_service import (
    campus_goal,
    confirm_trip,
    evaluate_badges,
    load_demo_trips,
    plan_commute,
)
from src.c2_application_service.achievements import counted_trips
from src.c2_application_service.recommendation import DEFAULT_MAX_EXTRA_MIN
from src.c3_data_adapter import confirmed_trips, reset_confirmed, sample_places

CAN_BE_INFEASIBLE = ("walk", "bike")  # modes the Commuter may mark not feasible (SRD 2.1.5)
GARDEN_SLOTS = 12  # trees drawn in the garden picture
EXAMPLES = (
    ("Collegetown", "Cornell Arts Quad"),
    ("Cornell Arts Quad", "Ithaca Commons"),
    ("Cornell Gates Hall", "Collegetown"),
)
SAFE_NEXT = ("/achievements", "/garden")


def parse_limits(form) -> tuple:
    """Validate the optional settings; return (kwargs for plan_commute, errors)."""
    errors, limits = [], {}
    limits["not_feasible"] = tuple(m for m in form.getlist("not_feasible_modes") if m in CAN_BE_INFEASIBLE)

    raw = form.get("max_extra_min", "").strip()
    try:
        limits["max_extra_min"] = float(raw) if raw else DEFAULT_MAX_EXTRA_MIN
        if not 0 <= limits["max_extra_min"] <= 240:
            raise ValueError
    except ValueError:
        errors.append("Extra minutes you accept must be a number from 0 to 240.")

    raw = form.get("transit_minutes", "").strip()
    limits["transit_minutes"] = None
    if raw:
        try:
            limits["transit_minutes"] = float(raw)
            if not 0 < limits["transit_minutes"] <= 300:
                raise ValueError
        except ValueError:
            errors.append("Bus time must be a number of minutes above 0 and at most 300.")
    return limits, errors


def _percent(into_next_g: float, goal_g: float) -> int:
    return round(100 * into_next_g / goal_g)


def create_app() -> Flask:
    app = Flask(__name__)

    def render_plan(values, plan=None, errors=()):
        return render_template(
            "plan.html",
            active="plan",
            places=sample_places(),
            examples=EXAMPLES,
            can_be_infeasible=CAN_BE_INFEASIBLE,
            values=values,
            plan=plan,
            errors=list(errors),
        )

    def form_values():
        values = request.form.to_dict()
        values["not_feasible_modes"] = request.form.getlist("not_feasible_modes")
        return values

    @app.route("/", methods=["GET", "POST"])
    @app.route("/compare", methods=["GET", "POST"])
    def plan_page():
        if request.method == "GET":
            return render_plan(
                {
                    "origin": request.args.get("origin", "")[:100],
                    "destination": request.args.get("destination", "")[:100],
                    "max_extra_min": f"{DEFAULT_MAX_EXTRA_MIN:g}",
                    "date": _date.today().isoformat(),
                }
            )

        values = form_values()
        errors = []
        origin, destination = values.get("origin", "").strip(), values.get("destination", "").strip()
        if not origin:
            errors.append("Enter where you are starting from.")
        if not destination:
            errors.append("Enter where you are going.")
        limits, limit_errors = parse_limits(request.form)
        errors += limit_errors
        if errors:
            return render_plan(values, errors=errors)

        plan = plan_commute(origin, destination, **limits)
        return render_plan(values, plan=plan, errors=plan.errors)

    @app.route("/confirm", methods=["POST"])
    def confirm_page():
        transit = request.form.get("transit_minutes", "").strip()
        try:
            transit_minutes = float(transit) if transit else None
        except ValueError:
            transit_minutes = None
        trip, new_badges, errors = confirm_trip(
            request.form.get("origin", ""),
            request.form.get("destination", ""),
            request.form.get("mode", ""),
            request.form.get("date", ""),
            transit_minutes,
        )
        if errors:
            return render_plan(form_values(), errors=errors)
        return redirect(url_for("done_page", index=len(confirmed_trips()) - 1, new=",".join(new_badges)))

    @app.route("/done/<int:index>")
    def done_page(index):
        trips = confirmed_trips()
        if not 0 <= index < len(trips):
            return redirect(url_for("plan_page"))
        before, after = campus_goal(trips[:index]), campus_goal(trips[: index + 1])
        wanted = {n for n in request.args.get("new", "").split(",") if n}
        new_badges = [b for b in evaluate_badges(trips) if b.earned and b.name in wanted]
        return render_template(
            "done.html",
            active="",
            trip=trips[index],
            goal=after,
            added_g=after.total_g - before.total_g,
            tree_gained=after.trees_reached > before.trees_reached,
            percent=_percent(after.into_next_g, after.goal_g),
            new_badges=new_badges,
        )

    @app.route("/achievements")
    def achievements_page():
        trips = confirmed_trips()
        badges = evaluate_badges(trips)
        return render_template(
            "achievements.html",
            active="achievements",
            trips=sorted(trips, key=lambda t: t.date, reverse=True),
            trip_count=len(trips),
            saved_g=round(sum(max(t.difference_g, 0) for t in counted_trips(trips))),
            badges=badges,
            earned=[b for b in badges if b.earned],
            todo=[b for b in badges if not b.earned],
        )

    @app.route("/garden")
    def garden_page():
        goal = campus_goal(confirmed_trips())
        return render_template(
            "garden.html",
            active="garden",
            goal=goal,
            slots=GARDEN_SLOTS,
            shown=min(goal.trees_reached, GARDEN_SLOTS),
            percent=_percent(goal.into_next_g, goal.goal_g),
        )

    def back():
        target = request.form.get("next", "")
        return redirect(target if target in SAFE_NEXT else url_for("achievements_page"))

    @app.route("/demo", methods=["POST"])
    def demo_page():
        load_demo_trips()
        return back()

    @app.route("/reset", methods=["POST"])
    def reset_page():
        reset_confirmed()
        return back()

    return app
