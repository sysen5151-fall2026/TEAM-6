"""Scenario definitions for the Chapter 10 modeling and simulation section.

One source of truth: the action diagrams, the sequence diagrams, the duration tables, the Monte Carlo
runs and the Innoslate build sheet are all generated from the data in this file, so they cannot disagree.

Scenario 1 (SC.1) is the trip-planning flow as it is built today (UC.3 Plan and Choose a Trip, with the
weather check of plan_commute): routes first, then the weather request, one after the other.
Scenario 2 (SC.2) is the alternative: the Reference Data Subsystem sends the route request and the
weather request at the same time (fork and join), everything else unchanged.

Durations are in seconds. ("normal", mean, standard deviation) or ("exponential", rate per second).
The durations were fixed BEFORE the product was measured (Section 6 of the report); they are the team's
engineering estimates and are justified one by one in WHY. Human actions (X.1) have no measurements yet.
"""

# Lane (branch asset) order, top to bottom. Number and name are the entities of model 11.3.
ASSETS = [
    ("X.1", "Commuter", "ext"),
    ("C.0.1", "Entry Subsystem", "int"),
    ("C.0.2", "Reference Data Subsystem", "int"),
    ("X.6", "Route Service", "ext"),
    ("X.3", "Open-Meteo", "ext"),
    ("C.0.3", "Estimation Subsystem", "int"),
    ("C.0.5", "Recommendation Subsystem", "int"),
    ("C.0.6", "Presentation Subsystem", "int"),
    ("C.0.4", "Records Subsystem", "int"),
]
ASSET_NAME = {n: f"{n} {t}" for n, t, _ in ASSETS}

# Existing input/output entities of model 11.3 are reused by name; the rest are new in model 11.4.
IO_EXISTING = {
    "Entry Form": "UC.1.2", "Trip Places": "UC.3.2", "Route Request": "UC.3.3", "Route Options": "UC.3.4",
    "Mode Comparison": "UC.3.5", "Mode Choice": "UC.3.7", "Trip Result and Progress": "UC.3.8",
    "Validated Commute Entry": "IO.12", "Weather Request": "IO.4", "Weather Forecast Data": "IO.5",
    "Emission Factor Record": "IO.14", "Trip Weather Forecast": "IO.15",
}

# (key, name, asset, distribution, inputs, output)
# key is the position inside the scenario; the action number is t.<scenario>.<position>.
# inputs are the input/outputs that must have arrived before the action can start (all of them).
_COMMON = {
    "open":     ("Open Trip Planner", "X.1", ("normal", 1.5, 0.4)),
    "form":     ("Present Entry Form", "C.0.1", ("normal", 0.15, 0.04)),
    "enter":    ("Enter Start and Destination", "X.1", ("normal", 14.0, 4.0)),
    "submit":   ("Submit Trip Request", "X.1", ("normal", 0.8, 0.2)),
    "validate": ("Validate Trip Entry", "C.0.1", ("normal", 0.03, 0.01)),
    "reqroute": ("Request Routes", "C.0.2", ("normal", 0.02, 0.005)),
    "route":    ("Return Routes", "X.6", ("normal", 0.6, 0.2)),
    "factor":   ("Select Emission Factors", "C.0.2", ("normal", 0.01, 0.003)),
    "estimate": ("Estimate Mode Emissions", "C.0.3", ("normal", 0.02, 0.005)),
    "reqwx":    ("Request Weather", "C.0.2", ("normal", 0.01, 0.003)),
    "wx":       ("Return Weather Forecast", "X.3", ("normal", 0.4, 0.1)),
    "resolve":  ("Resolve Trip Forecast", "C.0.2", ("normal", 0.01, 0.003)),
    "recommend": ("Recommend Feasible Mode", "C.0.5", ("normal", 0.02, 0.005)),
    "present":  ("Present Comparison", "C.0.6", ("normal", 0.25, 0.06)),
    "choose":   ("Choose Way", "X.1", ("normal", 12.0, 4.0)),
    "record":   ("Record Trip and Update Progress", "C.0.4", ("normal", 0.08, 0.02)),
    "display":  ("Display Trip Result", "C.0.6", ("normal", 0.15, 0.04)),
    "review":   ("Review Trip Result", "X.1", ("exponential", 0.2)),
}

WHY = {
    "open": "One tap on the bookmark or home-screen link and a look at the page title. Assumed; no timed sessions yet (pilot usability session of requirement 2.1.1 will replace it).",
    "form": "The server renders one small template and sends it over the campus or home network. Assumed from page size; checked by measurement in Section 6.",
    "enter": "Two place pickers: type two or three letters, wait for the suggestion list, tap a place; about 6 to 8 s each, with a spread for slow typists. Chosen so that the whole entry stays near the 30 s target of requirement 2.1.1 without meeting it by construction. Assumed.",
    "submit": "Move to the button and press it. Assumed.",
    "validate": "In-process checks of two text fields and the leaving time. Assumed to be a few milliseconds of work plus framework overhead.",
    "reqroute": "Build three routing requests (drive, walk, bike) and hand them to the thread pool. Assumed to be milliseconds.",
    "route": "OpenRouteService directions over HTTPS. The three profile requests run side by side, so the action takes about as long as the slowest one. A public routing service is assumed to answer a short city route in 0.3 to 1.0 s. Assumed; checked by measurement.",
    "factor": "Look up one factor per mode in the reviewed factor set held in memory. Assumed to be milliseconds.",
    "estimate": "Multiply distance by factor for six rows and compute the always-drive baseline. Arithmetic only.",
    "reqwx": "Build the query (coarse area and time only) and start the HTTPS call. Assumed to be milliseconds.",
    "wx": "Open-Meteo current-conditions call. Component requirement 5.5.3 allows at most 1.0 s for this call, so the mean is set well inside it; a free public API in the same region is assumed to answer in 0.2 to 0.6 s. Assumed; checked by measurement.",
    "resolve": "Pick the forecast hour and keep its timestamp. Assumed to be milliseconds.",
    "recommend": "Apply the weather and time rules to six rows and pick the lowest CO2e. Assumed to be milliseconds.",
    "present": "Render the comparison page, including the map data for the routes. The largest page of the flow, so the largest system-side render time. Assumed.",
    "choose": "Read the compared ways, then tap one. Includes reading time. Assumed; no timed sessions yet.",
    "record": "One database insert for the trip and the badge check. Assumed to be tens of milliseconds.",
    "display": "Render the result page (saving, tree progress). A smaller page than the comparison. Assumed.",
    "review": "Open-ended pause after the result: many short, a few long. An exponential distribution with mean 5 s (rate 0.2 per second) has that shape, as the lab manual uses it for the customer entry. Assumed.",
}

# Flow per scenario: key -> (inputs, output). Same names for the same step in both scenarios.
SC1_FLOW = {
    "open":     ([], "Planner Request"),
    "form":     (["Planner Request"], "Entry Form"),
    "enter":    (["Entry Form"], "Trip Places"),
    "submit":   (["Trip Places"], "Trip Request"),
    "validate": (["Trip Request"], "Validated Commute Entry"),
    "reqroute": (["Validated Commute Entry"], "Route Request"),
    "route":    (["Route Request"], "Route Options"),
    "factor":   (["Route Options"], "Emission Factor Record"),
    "estimate": (["Route Options", "Emission Factor Record"], "Mode Comparison"),
    "reqwx":    (["Mode Comparison"], "Weather Request"),          # as built: only after the comparison is complete
    "wx":       (["Weather Request"], "Weather Forecast Data"),
    "resolve":  (["Weather Forecast Data"], "Trip Weather Forecast"),
    "recommend": (["Mode Comparison", "Trip Weather Forecast"], "Mode Recommendation"),
    "present":  (["Mode Comparison", "Mode Recommendation"], "Comparison View"),
    "choose":   (["Comparison View"], "Mode Choice"),
    "record":   (["Mode Choice"], "Trip Result and Progress"),
    "display":  (["Trip Result and Progress"], "Trip Result View"),
    "review":   (["Trip Result View"], "Review Note"),
}
SC2_FLOW = dict(SC1_FLOW)
SC2_FLOW.update({
    "reqwx":    (["Validated Commute Entry"], "Weather Request"),   # alternative: weather asked at the same time as the routes
    "factor":   (["Validated Commute Entry"], "Emission Factor Record"),
})

SCENARIOS = {
    1: {
        "id": "SC.1", "title": "Sequential Trip Planning (as built)",
        "flow": SC1_FLOW,
        "order": ["open", "form", "enter", "submit", "validate", "reqroute", "route", "factor", "estimate", "reqwx", "wx", "resolve", "recommend", "present", "choose", "record", "display", "review"],
        "summary": "The Reference Data Subsystem asks the Route Service for the routes, selects the factors, and only after the Estimation Subsystem has produced the comparison does it ask Open-Meteo for the weather. This is the order of plan_commute in the product.",
    },
    2: {
        "id": "SC.2", "title": "Concurrent Dispatch (alternative)",
        "flow": SC2_FLOW,
        "order": ["open", "form", "enter", "submit", "validate", "reqroute", "reqwx", "route", "wx", "factor", "resolve", "estimate", "recommend", "present", "choose", "record", "display", "review"],
        "summary": "Right after validation the Reference Data Subsystem sends the route request, then the weather request, then the factor lookup, without waiting for either answer; the Route Service and Open-Meteo answer side by side and their answers are joined before estimation and recommendation. Same actions and the same duration distributions as SC.1; only the control flow differs.",
    },
}


def actions(sc):
    """The actions of scenario sc as dicts, in listing order, with numbers t.<sc>.<n>."""
    s = SCENARIOS[sc]
    out = []
    for n, key in enumerate(s["order"], 1):
        name, asset, dist = _COMMON[key]
        ins, outp = s["flow"][key]
        out.append({
            "key": key, "num": f"t.{sc}.{n}", "n": n, "name": name, "asset": asset, "dist": dist,
            "inputs": list(ins), "output": outp, "why": WHY[key],
        })
    return out


def dist_text(dist):
    if dist[0] == "normal":
        return f"Normal, mean {dist[1]:g} s, SD {dist[2]:g} s"
    return f"Exponential, rate {dist[1]:g} per s (mean {1 / dist[1]:g} s)"


def dist_cols(dist):
    """(distribution name, 'mean or rate', SD) as in the lab manual's duration tables."""
    if dist[0] == "normal":
        return "Normal", f"{dist[1]:g}", f"{dist[2]:g}"
    return "Exponential", f"λ = {dist[1]:g}", ""
