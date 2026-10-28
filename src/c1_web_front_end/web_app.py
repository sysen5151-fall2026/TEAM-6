"""Web pages for C.1.

Flow: plan (start and destination are required, every way is compared) ->
choose a way -> done page (saving, tree progress, new badges) -> garden and
achievements pages to look back. The pages only collect input and show what
C.2 returns; no calculation or rule lives here.

Run:  python -m src.main_web
"""

import math
from datetime import date as _date
from datetime import datetime

from datetime import datetime as _dt

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

from src.c1_web_front_end import auth
from src.c2_application_service import (
    accounts,
    campus_goal,
    confirm_trip,
    evaluate_badges,
    find_bus,
    load_demo_trips,
    local_now,
    plan_commute,
    preview_routes,
)
from src.c2_application_service.achievements import counted_trips, earned_dates
from src.c2_application_service.plan import VEHICLES
from src.c3_data_adapter import (
    place_search_is_live,
    search_paused,
    suggest_places,
)
from src.interfaces import Place
from src.model_trace import realizes

GARDEN_SLOTS = 12  # trees drawn in the garden picture
SAFE_NEXT = ("/achievements", "/garden")


def parse_have(form) -> tuple:
    """The vehicles the Commuter ticked; the student has none by default."""
    return tuple(v for v in VEHICLES if v in form.getlist("have"))


WHEN_FORMATS = ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")


def parse_when(raw) -> tuple:
    """The leaving time from the form as (datetime, error). Empty means now, Ithaca time."""
    raw = (raw or "").strip()
    if not raw:
        return local_now(), ""
    for fmt in WHEN_FORMATS:
        try:
            when = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if 2020 <= when.year <= 2100:
            return when, ""
    return None, "Enter when you are leaving as a date and a time."


def _percent(into_next_g: float, goal_g: float) -> int:
    return round(100 * into_next_g / goal_g)


def _map_places(plan) -> list:
    """Start and destination of a finished plan, for the map (empty before a plan exists)."""
    if plan is None or not plan.comparisons:
        return []
    return [
        {"kind": kind, "label": place.label, "lat": place.lat, "lon": place.lon}
        for kind, place in (("origin", plan.origin), ("destination", plan.destination))
    ]


def recent_pairs(trips, limit=4) -> list:
    """The latest distinct start and destination pairs this account has recorded (never a raw position)."""
    seen, pairs = set(), []
    for t in reversed(trips):
        pair = (t.origin, t.destination)
        if pair not in seen and not t.origin.startswith("My location") and not t.destination.startswith("My location"):
            seen.add(pair)
            pairs.append(pair)
    return pairs[:limit]


@realizes("UC.3.6")
def render_plan(values, plan=None, errors=()):
    when, _ = parse_when(values.get("when"))
    when = when or local_now()
    today = _date.today()
    return render_template(
        "plan.html",
        active="plan",
        live_search=place_search_is_live(),
        map_places=_map_places(plan),
        bus_cards=_bus_cards(plan),
        vehicles=VEHICLES,
        today=today.isoformat(),
        when_value=when.strftime("%Y-%m-%dT%H:%M"),
        confirm_date=min(when.date(), today).isoformat(),  # a trip can only be confirmed once it has happened
        restore_have=False,  # the account remembers it, not the browser
        recent=recent_pairs(g.trips.all()),
        values=values,
        plan=plan,
        errors=list(errors),
    )


def form_values():
    values = request.form.to_dict()
    values["have"] = list(parse_have(request.form))  # only known vehicles reach the page
    return values


def plan_page():
    if request.method == "GET":
        have = [v for v in accounts.get_prefs(g.db, g.user["id"]).get("have", []) if v in VEHICLES]
        return render_plan(
            {
                "origin": request.args.get("origin", "")[:100],
                "destination": request.args.get("destination", "")[:100],
                "have": have,
            }
        )

    values = form_values()
    errors = []
    origin, destination = values.get("origin", "").strip(), values.get("destination", "").strip()
    if not origin:
        errors.append("Enter where you are starting from.")
    if not destination:
        errors.append("Enter where you are going.")
    when, when_error = parse_when(values.get("when"))
    if when_error:
        errors.append(when_error)
    if errors:
        return render_plan(values, errors=errors)

    accounts.set_pref(g.db, g.user["id"], "have", list(parse_have(request.form)))  # remembered for next time
    plan = plan_commute(origin, destination, have=parse_have(request.form), when=when,
                        bus_route=values.get("bus_route", ""))
    return render_plan(values, plan=plan, errors=plan.errors)


def parse_share(form) -> tuple:
    """(mode, people) for the drive card: "Alone" is a drive, "Carpool" a carpool of that many people."""
    mode = form.get("mode", "")
    if mode == "drive" and form.get("share") == "carpool":
        try:
            return "carpool", int(form.get("occupants", ""))
        except ValueError:
            return "carpool", 0  # the trip is refused with a message about the number of people
    return mode, 1


def confirm_page():
    when, _ = parse_when(request.form.get("when"))  # a bad value means "now"
    mode, people = parse_share(request.form)
    trip, new_badges, errors = confirm_trip(
        request.form.get("origin", ""),
        request.form.get("destination", ""),
        mode,
        request.form.get("date", ""),
        parse_have(request.form),
        when,
        people,
        request.form.get("bus_route", ""),
        g.trips,
        auth.community_trips(),
    )
    if errors:
        return render_plan(form_values(), errors=errors)
    return redirect(url_for("done_page", index=len(g.trips.all()) - 1, new=",".join(new_badges)))


@realizes("UC.3.9")
def done_page(index):
    trips = g.trips.all()
    if not 0 <= index < len(trips):
        return redirect(url_for("plan_page"))
    community = auth.community_trips()
    before, after = campus_goal(trips[:index], community), campus_goal(trips[: index + 1], community)
    wanted = {n for n in request.args.get("new", "").split(",") if n}
    new_badges = [b for b in evaluate_badges(trips, community) if b.earned and b.name in wanted]
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


@realizes("UC.3.10")
def achievements_page():
    trips = g.trips.all()
    community = auth.community_trips()
    badges = evaluate_badges(trips, community)
    return render_template(
        "achievements.html",
        active="achievements",
        trips=sorted(trips, key=lambda t: t.date, reverse=True),
        trip_count=len(trips),
        saved_g=round(sum(max(t.difference_g, 0) for t in counted_trips(trips))),
        badges=badges,
        earned=[b for b in badges if b.earned],
        earned_on=earned_dates(trips, community),
        todo=[b for b in badges if not b.earned],
    )


@realizes("UC.3.10")
def garden_page():
    goal = campus_goal(g.trips.all(), auth.community_trips())
    return render_template(
        "garden.html",
        active="garden",
        goal=goal,
        slots=GARDEN_SLOTS,
        shown=min(goal.trees_reached, GARDEN_SLOTS),
        percent=_percent(goal.into_next_g, goal.goal_g),
    )


def places_api():
    """Places matching the text typed so far, for the suggestion list.

    quick=1 answers at once from sample places and what is already known, without asking
    the online service; the page asks again without it a moment after the last key.
    """
    quick = request.args.get("quick") == "1"
    places = suggest_places(request.args.get("q", ""), online=not quick)
    return jsonify(
        {
            "places": [{"label": p.label, "lat": p.lat, "lon": p.lon} for p in places],
            "online": place_search_is_live(),
            "paused": search_paused(),
        }
    )


def _coordinate(name: str, low: float, high: float) -> float:
    value = float(request.args[name])
    if not (math.isfinite(value) and low <= value <= high):
        raise ValueError(name)
    return value


def _option_json(bus) -> dict:
    """One bus option for the map: its route, times, stops and line."""
    return {
        "route_id": bus.route_id, "route": bus.route_name, "color": bus.color, "headsign": bus.headsign,
        "depart": bus.depart_time, "arrive": bus.arrive_time, "leave": bus.leave_time,
        "walk_to_min": bus.walk_to_min, "ride_min": bus.ride_min, "walk_from_min": bus.walk_from_min,
        "board": {"name": bus.board.name, "lat": bus.board.lat, "lon": bus.board.lon},
        "alight": {"name": bus.alight.name, "lat": bus.alight.lat, "lon": bus.alight.lon},
        "path": [[lat, lon] for lat, lon in bus.path],
    }


def _bus_json(result) -> dict:
    """The bus for the map: the best option's fields at the top, every option under "options", else why not."""
    out = {"status": result.status, "note": result.note}
    if result.options:
        out.update(_option_json(result.options[0]))
        out["options"] = [_option_json(o) for o in result.options]
    return out


def _bus_cards(plan) -> list:
    """What the page script needs to switch the bus card between the routes that link the places."""
    if plan is None or not plan.bus or not plan.bus.options:
        return []
    cards = []
    for option, row in zip(plan.bus.options, plan.bus_rows):
        cards.append({
            "route_id": option.route_id, "route": option.route_name, "color": option.color,
            "text_color": option.text_color, "headsign": option.headsign,
            "board": option.board.name, "alight": option.alight.name,
            "depart": option.depart_time, "arrive": option.arrive_time, "leave": option.leave_time,
            "arrive_destination": option.arrive_destination, "next": list(option.next_departures),
            "walk_to_min": option.walk_to_min, "walk_to_m": option.walk_to_m,
            "walk_from_min": option.walk_from_min, "walk_from_m": option.walk_from_m,
            "ride_min": option.ride_min, "total_min": row.duration_min, "ride_km": row.distance_km,
            "co2e_g": row.co2e_g, "difference_g": row.difference_g,
        })
    return cards


def route_lines_api():
    """Drive, walk and bike lines between two points, and the bus if there is one, for the map."""
    try:
        origin = Place("", _coordinate("olon", -180, 180), _coordinate("olat", -90, 90), "map")
        dest = Place("", _coordinate("dlon", -180, 180), _coordinate("dlat", -90, 90), "map")
    except (KeyError, ValueError):
        return jsonify({"error": "Give olat, olon, dlat and dlon as coordinates."}), 400
    when, when_error = parse_when(request.args.get("when"))
    if when_error:
        return jsonify({"error": when_error}), 400
    options, error = preview_routes(origin, dest)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(
        {
            "bus": _bus_json(find_bus(origin, dest, when)),
            "routes": [
                {
                    "mode": o.mode,
                    "distance_km": o.distance_km,
                    "duration_min": o.duration_min,
                    "estimated": o.source != "OpenRouteService",
                    "path": [[lat, lon] for lat, lon in o.path],
                }
                for o in options
            ]
        }
    )


def back():
    target = request.form.get("next", "")
    return redirect(target if target in SAFE_NEXT else url_for("achievements_page"))


def demo_page():
    load_demo_trips(g.trips)
    return back()


def reset_page():
    g.trips.clear()
    return back()


def create_app(db_path=None) -> Flask:
    """The web application. db_path is the account database (default data/app.sqlite)."""
    app = Flask(__name__)
    app.jinja_env.filters["epoch_date"] = lambda ts: _dt.fromtimestamp(ts).strftime("%b %d, %Y").replace(" 0", " ")
    auth.init_auth(app, db_path)
    app.add_url_rule("/", view_func=plan_page, methods=["GET", "POST"])
    app.add_url_rule("/compare", view_func=plan_page, methods=["GET", "POST"])
    app.add_url_rule("/places", view_func=places_api)
    app.add_url_rule("/route-lines", view_func=route_lines_api)
    app.add_url_rule("/confirm", view_func=confirm_page, methods=["POST"])
    app.add_url_rule("/done/<int:index>", view_func=done_page)
    app.add_url_rule("/achievements", view_func=achievements_page)
    app.add_url_rule("/garden", view_func=garden_page)
    app.add_url_rule("/demo", view_func=demo_page, methods=["POST"])
    app.add_url_rule("/reset", view_func=reset_page, methods=["POST"])
    return app
