"""Chapter 11 and 12 analysis: criteria, value functions, swing weights, value scores, sensitivity, life cycle cost,
affordability, and the risk table. One source for every number in the report.

    python docs/ch11/sim/model.py            writes docs/ch11/data/analysis.json

Inputs are the measured files in docs/ch11/data (spikes) and docs/ch10/data (the Chapter 10 campaign). Judgments
(importance of each criterion, risk ratings, labour hours and rate) are written here in one place, labelled as such,
so the team can change one line and rerun.
"""
import csv
import json
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D11 = os.path.join(ROOT, "docs", "ch11", "data")
D10 = os.path.join(ROOT, "docs", "ch10", "data")

ALTS = {
    "A": "Sequential dispatch (as built)",
    "B": "Concurrent dispatch",
    "C": "Concurrent dispatch with keep-alive",
    "D": "Concurrent dispatch with name cache",
    "E": "Queued asynchronous handling",
}

# ------------------------------------------------------------------------------------------ criteria
# id, name, unit, best (value 100), worst (value 0), importance (team judgment, H/M/L) and why, traced requirement and need.
CRITERIA = [
    dict(id="EC.1", name="Result time when connections must be re-opened", unit="share of plans within 3 s (%)", best=100.0, worst=0.0,
         importance="H", why="Requirement 3.4.2.1 is a shall and the cold case is the normal case between commuters (Chapter 10 Section 7.4).",
         req="2.1.2, 3.4.2.1, 5.5.3", need="1.1.1"),
    dict(id="EC.2", name="Typical result time", unit="median plan response, warm (s)", best=0.1, worst=3.0, importance="M",
         why="The warm product already answers in about 0.2 s, so a faster median matters less than the worst case.",
         req="2.1.2, 3.4.2.1", need="1.1.1"),
    dict(id="EC.3", name="Time to first feedback", unit="submit to first visible response (s)", best=0.05, worst=3.0, importance="M",
         why="A commuter who sees nothing for seconds may press again; the 3 s display limit is the outer bound.",
         req="2.1.2", need="1.1.1"),
    dict(id="EC.4", name="Moving parts to build and verify", unit="count of new threads, loops, endpoints, stores, scripts", best=0.0, worst=6.0,
         importance="M", why="The pilot results are due 18 December 2026 (3.4.1.2) and every new part needs tests.",
         req="3.4.1.2", need="1.3.2"),
    dict(id="EC.5", name="New states to check for accessibility", unit="count of new interaction states", best=0.0, worst=4.0, importance="H",
         why="WCAG 2.2 AA is a shall for the entry and result views (3.4.4.1) and a waiting page adds states a screen-reader user must be told about.",
         req="3.4.4.1", need="1.1.7, 1.5.3"),
    dict(id="EC.6", name="Headroom under the free service limits", unit="share of Open-Meteo free daily limit used (%)", best=0.0, worst=100.0,
         importance="M", why="The free plans have daily limits and no uptime promise; a pilot that uses most of one is one busy day from a refusal (TR.11).",
         req="5.5.5, 2.3.1", need="1.2.3"),
]
# swing weight matrix: rows importance, columns variation (the range of the value scores across the alternatives)
SWING = {("H", "H"): 100, ("H", "M"): 80, ("H", "L"): 60,
         ("M", "H"): 70, ("M", "M"): 50, ("M", "L"): 30,
         ("L", "H"): 40, ("L", "M"): 20, ("L", "L"): 10}
VARIATION_BREAKS = (50.0, 20.0)   # range of value scores: >= 50 high, >= 20 medium, else low


def value(c, x):
    lo, hi = c["worst"], c["best"]
    v = 100.0 * (x - lo) / (hi - lo)
    return max(0.0, min(100.0, v))


# ------------------------------------------------------------------------------------------ data
def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def exists(name):
    return os.path.exists(os.path.join(D11, name))


def measurements():
    out = {"notes": []}
    gap, gap_parts = {}, {}
    for a in "ABCD":
        name = f"dispatch_gap_{a}.csv"
        if exists(name):
            rows = read(os.path.join(D11, name))
            gap[a] = [float(r["plan_s"]) for r in rows]
            gap_parts[a] = [(float(r["route_max_s"]), float(r["weather_s"])) for r in rows]
    warm = {}
    if exists("dispatch_warm.csv"):
        for r in read(os.path.join(D11, "dispatch_warm.csv")):
            warm.setdefault(r["strategy"], []).append(float(r["plan_s"]))
    out["gap"], out["warm"], out["gap_parts"] = gap, warm, gap_parts
    # E: queued handling is replayed on B (the worker does what B does): result time = B's + queue hand-off + the wait for
    # the next poll (uniform on 0..poll interval)
    poll, hand_off = 0.5, 0.002
    rnd = random.Random(5151)
    if "B" in gap:
        out["gap"]["E"] = [t + hand_off + rnd.uniform(0, poll) for t in gap["B"]]
    out["poll_interval_s"], out["hand_off_s"] = poll, hand_off
    return out


def parts_and_states():
    # Design counts (the team's own, from the designs in Section 3 of the report)
    # B: a thread pool call site; C: B + keep-alive loop; D: B + name cache module + connection class;
    # E: B + queue and worker, job table, status endpoint, polling script, expiry job
    parts = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 6}
    states = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 3}  # E: waiting, ready, failed or timed out
    return parts, states


def free_limit_share(plans_per_day, keepalive_s):
    """Open-Meteo free plan: 10,000 calls a day (https://open-meteo.com/en/terms). One call per plan, one per confirmed trip
    (the second plan_commute inside confirm_trip, Chapter 10 Check 3) and, for C, one per keep-alive interval."""
    daily = plans_per_day * 2 + (86400 / keepalive_s if keepalive_s else 0)
    return 100.0 * daily / 10000.0


PLANS_PER_DAY = 500    # ASSUMPTION: 500 accounts (requirement 3.4.3.2 pilot size) each plan and confirm about one trip a day
KEEPALIVE_S = 20


def scores(meas):
    parts, states = parts_and_states()
    raw = {}
    gap, warm = meas["gap"], meas["warm"]
    for a in ALTS:
        g = gap.get(a, [])
        w = warm.get("A" if a == "A" else "B", [])   # warm: B stands for C, D and E (same code once connections are open)
        first_response = 0.003 if a == "E" else (statistics.median(g) if g else None)  # E: validate 1.4 ms + render 0.5 ms (Chapter 10) + hand-off
        raw[a] = {
            "EC.1": 100.0 * sum(t <= 3 for t in g) / len(g) if g else None,
            "EC.2": (statistics.median(w) + (0.25 + 0.002 if a == "E" else 0)) if w else None,
            "EC.3": first_response,
            "EC.4": parts[a],
            "EC.5": states[a],
            "EC.6": free_limit_share(PLANS_PER_DAY, KEEPALIVE_S if a == "C" else 0),
        }
    return raw


def swing_weights(raw):
    rows = []
    for c in CRITERIA:
        vs = [value(c, raw[a][c["id"]]) for a in ALTS]
        rng = max(vs) - min(vs)
        var = "H" if rng >= VARIATION_BREAKS[0] else "M" if rng >= VARIATION_BREAKS[1] else "L"
        rows.append({**c, "range": rng, "variation": var, "swing": SWING[(c["importance"], var)]})
    total = sum(r["swing"] for r in rows)
    for r in rows:
        r["weight"] = r["swing"] / total
    return rows


def totals(raw, weights):
    res = {}
    for a in ALTS:
        res[a] = {"values": {r["id"]: value(r, raw[a][r["id"]]) for r in weights}}
        res[a]["score"] = sum(r["weight"] * res[a]["values"][r["id"]] for r in weights)
    return res


def sensitivity(raw, weights):
    """One-at-a-time: each weight scaled from 0 to 3 times its value (others renormalised); and 10,000 random weightings."""
    ids = [r["id"] for r in weights]
    base = {r["id"]: r["weight"] for r in weights}
    vals = {a: {r["id"]: value(r, raw[a][r["id"]]) for r in weights} for a in ALTS}

    def winner(w):
        z = sum(w.values())
        sc = {a: sum(w[i] / z * vals[a][i] for i in ids) for a in ALTS}
        return max(sc, key=sc.get), sc

    sweep, flips = {}, {}
    for i in ids:
        sweep[i], prev = [], None
        for k in range(0, 61):
            f = k / 20.0
            w = dict(base)
            w[i] = base[i] * f
            win, sc = winner(w)
            sweep[i].append((f, win, sc))
            if prev is not None and win != prev:
                flips.setdefault(i, []).append((f, prev, win))
            prev = win
    rnd = random.Random(12)
    wins = {a: 0 for a in ALTS}
    for _ in range(10000):
        w = {i: rnd.random() ** 1.0 for i in ids}
        wins[winner(w)[0]] += 1
    # pairwise: weights that give the same total for the selected and the runner-up are on the flip points above
    return {"sweep": sweep, "flips": flips, "random_wins": {a: wins[a] / 10000 for a in ALTS}}


def whatif(raw, weights):
    """Scores of C and D when the assumed inputs of EC.6 change: plans per day and the keep-alive interval.
    C's measured times (EC.1, EC.3) are kept at their 20 s values for every interval: that is an assumption, not a measurement."""
    out = []
    for plans in (100, 500, 1000):
        for interval in (10, 20, 60):
            r = {a: dict(raw[a]) for a in ("C", "D")}
            r["C"]["EC.6"] = free_limit_share(plans, interval)
            r["D"]["EC.6"] = free_limit_share(plans, 0)
            sc = {}
            for a in ("C", "D"):
                sc[a] = sum(w["weight"] * value(w, r[a][w["id"]]) for w in weights)
            out.append({"plans": plans, "interval": interval, "C": sc["C"], "D": sc["D"], "winner": "C" if sc["C"] > sc["D"] else "D"})
    return out


# ------------------------------------------------------------------------------------------ life cycle cost
RATE = 75.0     # ASSUMPTION: loaded labour rate, US dollars per hour (team to confirm)
LIFE_YEARS = 3  # ASSUMPTION: pilot year plus two years of operation
LCC_INPUT = {
    #      build hours, verify hours (tests, accessibility), maintain hours per year, other cost per year
    "A": dict(build=0, verify=0, maintain=0, other=0),
    "B": dict(build=6, verify=6, maintain=2, other=0),
    "C": dict(build=10, verify=10, maintain=4, other=0),
    "D": dict(build=12, verify=12, maintain=4, other=0),
    "E": dict(build=40, verify=40, maintain=16, other=0),
}
BUDGET = {"C.0.2 Reference Data Subsystem share": 90000, "System baseline": 750000}


def lcc():
    out = {}
    for a, v in LCC_INPUT.items():
        hours = v["build"] + v["verify"] + v["maintain"] * LIFE_YEARS
        out[a] = {**v, "hours": hours, "labour": hours * RATE, "other": v["other"] * LIFE_YEARS,
                  "total": hours * RATE + v["other"] * LIFE_YEARS}
    return out


# ------------------------------------------------------------------------------------------ risks
# likelihood and impact are the team's engineering judgments (docs/risks.md); the numbers below are the draft the team reviews
IMPACT_WEIGHTS = {"tech": 0.5, "sched": 0.25, "cost": 0.25}
# The register (docs/risks.md) holds every product risk; the five of TABLE are the system-level risks of the Chapter 12 table.
# id, short name, AI-specific, L, technical, schedule, cost
REGISTER = [
    ("TR.16", "External service answers late and the 3-second display fails", False, 4, 5, 2, 2),
    ("TR.11", "Route service quota used up or host changed", False, 5, 2, 2, 3),
    ("TR.4", "Explanation states an unsupported or reversed fact (model output well formed but wrong)", True, 3, 4, 2, 1),
    ("TR.10", "Trips and places held finer than the coarse location allowed", False, 2, 5, 3, 4),
    ("TR.1", "Emission factor misapplied or outside its scope", False, 2, 3, 1, 2),
    ("TR.17", "Language model unavailable or too slow", True, 4, 1, 1, 1),
    ("TR.18", "Untrusted text from a data source reaches the prompt", True, 1, 4, 2, 2),
    ("TR.19", "Trip data leaves the machine by a path nobody intended", True, 2, 4, 2, 3),
    ("TR.20", "Response schema drifts between model or server versions", True, 2, 3, 2, 1),
    ("TR.21", "A dependency is abandoned, relicensed or moved", True, 3, 3, 3, 2),
    ("TR.22", "Assistant-written code or text is wrong and merged unreviewed", True, 3, 3, 2, 2),
    ("TR.13", "Timetable feed expires on 19 December 2026 and its terms are unknown", False, 4, 3, 2, 1),
    ("TR.14", "Account database on one computer holds personal data", False, 2, 4, 2, 3),
    ("TR.15", "Shared invite codes and plain http on a shared network", False, 3, 4, 2, 2),
    ("TR.7", "Hosting availability of 99.5 percent unproven", False, 3, 3, 2, 3),
]
TABLE = ("TR.16", "TR.11", "TR.4", "TR.10", "TR.1")
RISKS = [dict(id=i, short=n, ai=ai, L=L, tech=t, sched=sc, cost=c) for i, n, ai, L, t, sc, c in REGISTER]
BANDS = ((12.0, "High"), (6.0, "Medium"), (0.0, "Low"))


def risk_rows(only=None):
    out = []
    for r in RISKS:
        if only and r["id"] not in only:
            continue
        overall = sum(IMPACT_WEIGHTS[k] * r[k] for k in IMPACT_WEIGHTS)
        level = r["L"] * overall
        band = next(name for lim, name in BANDS if level >= lim)
        out.append({**r, "overall": overall, "overall_cell": max(1, min(5, int(overall + 0.5))), "level": level, "band": band})
    return sorted(out, key=lambda x: -x["level"])


def risk_table():
    return risk_rows(TABLE)


def stats_table(meas):
    out = {}
    for a, xs in meas["gap"].items():
        out[a] = {"n": len(xs), "median": statistics.median(xs), "mean": statistics.mean(xs), "p95": pct(xs, 95), "max": max(xs),
                  "within_3s": sum(x <= 3 for x in xs) / len(xs), "slow_runs": sum(x > 1.2 for x in xs)}
    return out


def select(tot, cost):
    """Highest effectiveness among the alternatives whose life cycle cost fits the budget share; ties go to the lower cost."""
    limit = min(BUDGET.values())
    ok = [a for a in tot if cost[a]["total"] <= limit]
    return max(ok, key=lambda a: (round(tot[a]["score"], 6), -cost[a]["total"]))


def main():
    meas = measurements()
    raw = scores(meas)
    weights = swing_weights(raw)
    tot = totals(raw, weights)
    sens = sensitivity(raw, weights)
    cost = lcc()
    summary = {a: {"n_gap": len(meas["gap"].get(a, [])), "n_warm": len(meas["warm"].get(a, []))} for a in ALTS}
    out = {"raw": raw, "weights": weights, "totals": tot, "sensitivity": {k: v for k, v in sens.items() if k != "sweep"},
           "sweep": sens["sweep"], "whatif": whatif(raw, weights), "lcc": cost, "risks": risk_table(), "register": risk_rows(), "n": summary,
           "selected": select(tot, cost),
           "measured": {"gap_runs": meas["gap"], "gap_stats": stats_table(meas), "gap_parts": meas["gap_parts"],
                        "warm_runs": meas["warm"], "poll_interval_s": meas["poll_interval_s"]},
           "budget": BUDGET, "free_limit": {"plans_per_day": PLANS_PER_DAY, "keepalive_s": KEEPALIVE_S},
           "assumptions": {"plans_per_day": PLANS_PER_DAY, "keepalive_s": KEEPALIVE_S, "rate": RATE, "life_years": LIFE_YEARS}}
    with open(os.path.join(D11, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    return out


if __name__ == "__main__":
    o = main()
    for a in ALTS:
        print(a, ALTS[a], {k: (round(v, 3) if v is not None else None) for k, v in o["raw"][a].items()}, round(o["totals"][a]["score"], 1), round(o["lcc"][a]["total"]))
    for w in o["weights"]:
        print(w["id"], w["importance"], w["variation"], w["swing"], round(w["weight"], 3), round(w["range"], 1))
    print("selected", o["selected"], o["sensitivity"]["random_wins"], o["sensitivity"]["flips"])
    for r in o["risks"]:
        print(r["id"], r["L"], round(r["overall"], 2), round(r["level"], 2), r["band"])
