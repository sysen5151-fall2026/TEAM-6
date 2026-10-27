"""Minimal web entry for C.1: a Flask page wrapping the existing UC.1 path.

The page only collects the Entry Form fields, validates them, hands a
CommuteRequest to C.2 through submit_commute_request and renders the
CommuteImpactResult. No calculation or rule lives here.

Run:  python -m src.main_web
"""

from datetime import date as _date

from flask import Flask, render_template, request

from src.c1_web_front_end.front_end import present_entry_fields, submit_commute_request
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

    return app
