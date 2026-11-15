"""Summaries and charts for the report: simulated distributions, measured stage timings, comparison.

    python docs/ch10/sim/analysis.py

Reads docs/ch10/data/{sim_*.csv, sim_results.json, measured_runs_{warm,cold}.csv}; writes
docs/ch10/data/analysis.json and the chart PNGs in docs/ch10/diagrams.
"""
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "diagrams")
SIM1, SIM2, WARM, COLD, GRAY = "#2E6DA4", "#C9731C", "#2A8C82", "#8B3E8F", "#6B7280"

# simulated action (SC.1) <-> measured field; sim mean from scenarios.py
STAGES = [
    ("t.1.2", "Present Entry Form", "C.0.1", "open_total", 0.15),
    ("t.1.5", "Validate Trip Entry", "C.0.1", "validate", 0.03),
    ("t.1.6", "Request Routes", "C.0.2", "request_routes", 0.02),
    ("t.1.7", "Return Routes", "X.6", "route_service", 0.60),
    ("t.1.8", "Select Emission Factors", "C.0.2", "select_factors", 0.01),
    ("t.1.9", "Estimate Mode Emissions", "C.0.3", "estimate", 0.02),
    ("t.1.10", "Request Weather", "C.0.2", "request_weather", 0.01),
    ("t.1.11", "Return Weather Forecast", "X.3", "weather_service", 0.40),
    ("t.1.12", "Resolve Trip Forecast", "C.0.2", "resolve", 0.01),
    ("t.1.13", "Recommend Feasible Mode", "C.0.5", "recommend", 0.02),
    ("t.1.14", "Present Comparison", "C.0.6", "present", 0.25),
    ("t.1.16", "Record Trip and Update Progress", "C.0.4", "record", 0.08),
    ("t.1.17", "Display Trip Result", "C.0.6", "display", 0.15),
]
SIM_SD = {"open_total": 0.04, "validate": 0.01, "request_routes": 0.005, "route_service": 0.2, "select_factors": 0.003, "estimate": 0.005,
          "request_weather": 0.003, "weather_service": 0.1, "resolve": 0.003, "recommend": 0.005, "present": 0.06, "record": 0.02, "display": 0.04}
NOT_MODELED = [("find_bus", "Bus planner call (no timetable index installed)"), ("replan", "Second plan_commute inside Choose Way"),
               ("replan_weather_call", "Second Open-Meteo call inside Choose Way"), ("geocode", "Geocoding of the two places (sample places, local)")]
AGG = [("plan_total", "Response time, plan page (submit to page returned)", "response_plan"),
       ("refdata", "Reference data return (validated entry to trip forecast returned)", "refdata"),
       ("result_total", "Response time, result page (choice submitted to result returned)", "response_result")]


def load(mode):
    with open(os.path.join(DATA, f"measured_runs_{mode}.csv")) as f:
        rows = list(csv.DictReader(f))
    return rows


def stat(v):
    v = np.asarray(v, float)
    return {"n": int(len(v)), "min": float(v.min()), "mean": float(v.mean()), "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
            "max": float(v.max()), "sd": float(v.std(ddof=1))}


def sim_col(sc, col):
    with open(os.path.join(DATA, f"sim_sc{sc}_mc_runs.csv")) as f:
        return np.array([float(r[col]) for r in csv.DictReader(f)])


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#E5E7EB", lw=0.6)
    ax.set_axisbelow(True)


def main():
    res = {}
    modes = {"warm": load("warm"), "cold": load("cold_nors")}
    if os.path.exists(os.path.join(DATA, "measured_runs_cold.csv")):
        modes["coldlive"] = load("cold")   # supplementary: cold connections with live routes
    for m, rows in modes.items():
        res[m] = {"n": len(rows), "ors_fail_runs": [int(r["run"]) for r in rows if r["ors_ok"] == "0"], "first_run": {c: float(rows[0][c]) for c in rows[0] if c not in ("run", "pair", "ors_ok")}}
        res[m]["stages"] = {c: stat([float(r[c]) for r in rows]) for c in rows[0] if c not in ("run", "pair", "ors_ok")}
        ok = [r for r in rows if r["ors_ok"] == "1"]
        res[m]["stages_ors_ok"] = {c: stat([float(r[c]) for r in ok]) for c in rows[0] if c not in ("run", "pair", "ors_ok")} if ok else {}
        res[m]["n_ok"] = len(ok)
        res[m]["within"] = {"plan_3s": float(np.mean([float(r["plan_total"]) <= 3.0 for r in rows])), "refdata_1_2": float(np.mean([float(r["refdata"]) <= 1.2 for r in rows])),
                            "weather_1_0": float(np.mean([float(r["weather_service"]) <= 1.0 for r in rows])), "result_3s": float(np.mean([float(r["result_total"]) <= 3.0 for r in rows]))}
    res["cold_slow_share"] = float(np.mean([float(r["weather_service"]) > 1.0 for r in modes["cold"]]))
    res["primary"] = {"warm": res["warm"]["stages_ors_ok"], "cold": res["cold"]["stages"], "coldlive": res.get("coldlive", {}).get("stages_ors_ok", {})}
    okrows = [r for r in modes["warm"] if r["ors_ok"] == "1"]
    res["warm"]["within_ok"] = {"plan_3s": float(np.mean([float(r["plan_total"]) <= 3.0 for r in okrows])), "refdata_1_2": float(np.mean([float(r["refdata"]) <= 1.2 for r in okrows])),
                                "weather_1_0": float(np.mean([float(r["weather_service"]) <= 1.0 for r in okrows])), "result_3s": float(np.mean([float(r["result_total"]) <= 3.0 for r in okrows]))}
    # warm excluding the very first run of the session
    w = okrows[1:]
    res["warm_after_first"] = {c: stat([float(r[c]) for r in w]) for c in w[0] if c not in ("run", "pair", "ors_ok")}
    # replay: what SC.2 would have given on the measured runs (concurrent dispatch removes the shorter of the two external calls from the response;
    # the reference data return then waits only for the weather call and the local steps). An estimate, not a measurement.
    for m, rows in modes.items():
        rows = [r for r in rows if r["ors_ok"] == "1"] if m in ("warm", "coldlive") else rows
        f = lambda r, c: float(r[c])
        p1 = [f(r, "plan_total") for r in rows]
        p2 = [f(r, "plan_total") - min(f(r, "route_service"), f(r, "weather_service")) for r in rows]
        r1 = [f(r, "refdata") for r in rows]
        r2 = [f(r, "weather_service") + f(r, "request_weather") + f(r, "resolve") + f(r, "select_factors") for r in rows]
        res[m]["replay"] = {
            "plan_sc1": stat(p1), "plan_sc2": stat(p2), "ref_sc1": stat(r1), "ref_sc2": stat(r2),
            "plan_sc1_3s": float(np.mean(np.array(p1) <= 3.0)), "plan_sc2_3s": float(np.mean(np.array(p2) <= 3.0)),
            "ref_sc1_1_2": float(np.mean(np.array(r1) <= 1.2)), "ref_sc2_1_2": float(np.mean(np.array(r2) <= 1.2)),
        }
    json.dump(res, open(os.path.join(DATA, "analysis.json"), "w"), indent=1)

    # ---- chart 1: simulated distributions SC.1 vs SC.2
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.3))
    for ax, col, thr, title, xmax in ((axs[0], "response_plan", 3.0, "Response time, plan page", 3.4), (axs[1], "refdata", 1.2, "Reference data return (requirement 5.5.3)", 2.0)):
        a, b = sim_col(1, col), sim_col(2, col)
        bins = np.linspace(0, xmax, 45)
        ax.hist(a, bins=bins, color=SIM1, alpha=0.78, label="SC.1 sequential", edgecolor="white", linewidth=0.4)
        ax.hist(b, bins=bins, color=SIM2, alpha=0.78, label="SC.2 concurrent", edgecolor="white", linewidth=0.4)
        ax.axvline(thr, color="#B42318", lw=1.4, ls="--")
        ax.text(thr, ax.get_ylim()[1] * 0.97, f" limit {thr:g} s", color="#B42318", fontsize=8, va="top", ha="left" if thr < xmax * 0.8 else "right")
        ax.set_title(title, fontsize=9.5, loc="left")
        ax.set_xlabel("seconds (1000 simulated runs each)", fontsize=8.5)
        ax.set_ylabel("runs", fontsize=8.5)
        style(ax)
        ax.tick_params(labelsize=8)
    axs[0].legend(fontsize=8, frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_sim_dist.png"), dpi=200, facecolor="white")
    plt.close(fig)

    # ---- chart 2: per-stage mean, simulated vs measured (log axis)
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    y = np.arange(len(STAGES))[::-1]
    h = 0.26
    simv = [s[4] for s in STAGES]
    wv = [res["warm"]["stages_ors_ok"][s[3]]["mean"] for s in STAGES]
    cv = [res["coldlive"]["stages_ors_ok"][s[3]]["mean"] for s in STAGES]
    floor = 1e-4
    ax.barh(y + h, np.maximum(simv, floor), h, color=SIM1, label="Simulated mean (SC.1)")
    ax.barh(y, np.maximum(wv, floor), h, color=WARM, label=f"Measured mean, warm connections ({res['warm']['n_ok']} runs with live routes)")
    ax.barh(y - h, np.maximum(cv, floor), h, color=COLD, label=f"Measured mean, cold connections ({res['coldlive']['n_ok']} runs, live routes)")
    ax.set_xscale("log")
    ax.set_xlim(floor, 10)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{s[0]} {s[1]}" for s in STAGES], fontsize=7.8)
    ax.set_xlabel("seconds (logarithmic axis)", fontsize=8.5)
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", color="#E5E7EB", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=7.8, frameon=False, loc="upper center", bbox_to_anchor=(0.42, -0.09), ncol=1)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_stage_compare.png"), dpi=200, facecolor="white")
    plt.close(fig)

    # ---- chart 3: measured plan response vs simulated
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    wv = [float(r["plan_total"]) for r in modes["warm"] if r["ors_ok"] == "1"]
    cv = [float(r["plan_total"]) for r in modes["cold"]]
    clv = [float(r["plan_total"]) for r in modes["coldlive"]]
    sv = sim_col(1, "response_plan")
    bins = np.linspace(0, max(max(cv), max(float(r["plan_total"]) for r in modes["coldlive"]), 3.6) * 1.02, 60)
    ax.hist(sv, bins=bins, color=SIM1, alpha=0.55, label="Simulated SC.1 (1000 runs)", weights=np.ones(len(sv)) / len(sv) * 100, edgecolor="white", linewidth=0.3)
    ax.hist(wv, bins=bins, color=WARM, alpha=0.85, label=f"Measured, warm, live routes ({len(wv)} runs)", weights=np.ones(len(wv)) / len(wv) * 100, edgecolor="white", linewidth=0.3)
    ax.hist(cv, bins=bins, color=COLD, alpha=0.75, label=f"Measured, cold, no live routes ({len(cv)} runs)", weights=np.ones(len(cv)) / len(cv) * 100, edgecolor="white", linewidth=0.3)
    ax.hist(clv, bins=bins, color="#C9731C", alpha=0.85, label=f"Measured, cold, live routes ({len(clv)} runs)", weights=np.ones(len(clv)) / len(clv) * 100, edgecolor="white", linewidth=0.3)
    ax.axvline(3.0, color="#B42318", lw=1.4, ls="--")
    ax.text(3.02, ax.get_ylim()[1] * 0.95, "limit 3 s", color="#B42318", fontsize=8, va="top")
    ax.set_xlabel("seconds from submit to plan page returned", fontsize=8.5)
    ax.set_ylabel("share of runs (%)", fontsize=8.5)
    ax.legend(fontsize=8, frameon=False)
    style(ax)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_measured_plan.png"), dpi=200, facecolor="white")
    plt.close(fig)
    print(json.dumps({m: {"n": res[m]["n"], "ors_fail_runs": res[m]["ors_fail_runs"], "within": res[m]["within"]} for m in ("warm", "cold")}, indent=1))


if __name__ == "__main__":
    main()
