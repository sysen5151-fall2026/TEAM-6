"""Minimal web entry for C.1: a Flask page wrapping the existing UC.1 path.

The page only collects the Entry Form fields, validates them, hands a
CommuteRequest to C.2 through submit_commute_request and renders the
CommuteImpactResult. No calculation or rule lives here.

Run:  python -m src.main_web
"""

from datetime import date as _date

from flask import Flask, redirect, render_template, request, url_for

from src.c1_web_front_end.front_end import present_entry_fields, submit_commute_request
from src.c2_application_service import (
    campus_goal,
    confirm_trip,
    evaluate_badges,
    load_demo_trips,
    plan_commute,
)
from src.c2_application_service.recommendation import DEFAULT_MAX_EXTRA_MIN
from src.c3_data_adapter import confirmed_trips, reset_confirmed, sample_places
from src.interfaces import CommuteRequest

MODES = ("drive", "carpool", "bus", "bike", "walk")
CAN_BE_INFEASIBLE = ("walk", "bike")  # modes the Commuter may mark not feasible (SRD 2.1.5)
MAX_DISTANCE_KM = 500.0


def parse_entry(form) -> tuple:
    """Validate the submitted fields; return (CommuteRequest | None, errors)."""
    errors = []

    mode = form.get("mode", "")
    if mode not in MODES:
        errors.append("Choose a travel mode from the list.")

    distance_km = 0.0
    try:
        distance_km = float(form.get("distance_km", ""))
        if not 0 < distance_km <= MAX_DISTANCE_KM:
            raise ValueError
    except ValueError:
        errors.append(f"Distance must be a number above 0 and at most {MAX_DISTANCE_KM:g} km.")

    day = form.get("date", "")
    try:
        _date.fromisoformat(day)
    except ValueError:
        errors.append("Enter the trip date as YYYY-MM-DD.")

    coarse_area = form.get("coarse_area", "").strip()
    if not coarse_area:
        errors.append("Enter a coarse area such as a city name.")

    if errors:
        return None, errors

    not_feasible = tuple(m for m in form.getlist("not_feasible_modes") if m in CAN_BE_INFEASIBLE)
    return (
        CommuteRequest(
            mode=mode,
            distance_km=distance_km,
            date=day,
            coarse_area=coarse_area,
            not_feasible_modes=not_feasible,
        ),
        [],
    )


def parse_limits(form) -> tuple:
    """Validate the optional compare-page settings; return (kwargs for plan_commute, errors)."""
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


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def commute_page():
        present_entry_fields()  # the same field list the CLI path uses
        values = {"date": _date.today().isoformat(), "coarse_area": "Ithaca, NY"}
        result, errors = None, []
        if request.method == "POST":
            values = request.form.to_dict()
            values["not_feasible_modes"] = request.form.getlist("not_feasible_modes")
            commute, errors = parse_entry(request.form)
            if commute is not None:
                result = submit_commute_request(commute)
        return render_template(
            "commute.html",
            modes=MODES,
            can_be_infeasible=CAN_BE_INFEASIBLE,
            values=values,
            errors=errors,
            result=result,
        )

    @app.route("/compare", methods=["GET", "POST"])
    def compare_page():
        values = {"max_extra_min": f"{DEFAULT_MAX_EXTRA_MIN:g}", "date": _date.today().isoformat()}
        plan, errors = None, []
        if request.method == "POST":
            values = request.form.to_dict()
            values["not_feasible_modes"] = request.form.getlist("not_feasible_modes")
            limits, errors = parse_limits(request.form)
            if not errors:
                plan = plan_commute(
                    request.form.get("origin", ""),
                    request.form.get("destination", ""),
                    **limits,
                )
                errors = list(plan.errors)
        return render_template(
            "compare.html",
            places=sample_places(),
            can_be_infeasible=CAN_BE_INFEASIBLE,
            values=values,
            plan=plan,
            errors=errors,
        )

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
            return render_achievements(errors=errors)
        return redirect(url_for("achievements_page", confirmed=trip.mode, new=",".join(new_badges)))

    @app.route("/achievements")
    def achievements_page():
        new = [n for n in request.args.get("new", "").split(",") if n]
        return render_achievements(confirmed=request.args.get("confirmed", ""), new_badges=new)

    @app.route("/demo", methods=["POST"])
    def demo_page():
        load_demo_trips()
        return redirect(url_for("achievements_page"))

    @app.route("/reset", methods=["POST"])
    def reset_page():
        reset_confirmed()
        return redirect(url_for("achievements_page"))

    def render_achievements(errors=(), confirmed="", new_badges=()):
        trips = confirmed_trips()
        return render_template(
            "achievements.html",
            badges=evaluate_badges(trips),
            goal=campus_goal(trips),
            trip_count=len(trips),
            errors=list(errors),
            confirmed=confirmed,
            new_badges=list(new_badges),
        )

    return app
