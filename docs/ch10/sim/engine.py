"""Discrete-event / Monte Carlo engine for the action diagrams of scenarios.py.

Semantics (the same as the Innoslate action diagram simulator for this kind of diagram, built with one branch per asset):
an action starts when all of its input/outputs (triggers) have been generated and the previous action of its own branch has ended; it runs for a duration sampled from
its distribution; it then generates its output. The scenario ends when the last action ends. Actions
with no dependence on each other run at the same time.

Everything is NumPy with an explicit seed, so a run set can be reproduced exactly.
"""
import numpy as np

import scenarios as S


def sample(dist, rng):
    if dist[0] == "normal":
        return max(0.0, float(rng.normal(dist[1], dist[2])))
    return float(rng.exponential(1.0 / dist[1]))


def run_once(sc, rng, acts=None):
    """One run: returns {action key: (start, end)} in seconds."""
    acts = acts or S.actions(sc)
    produced = {}   # input/output name -> time it exists
    times = {}
    # one branch per asset: an asset starts its next action (in the listing order) only after it has finished the previous one
    prev, last = {}, {}
    for a in acts:
        prev[a["key"]] = last.get(a["asset"])
        last[a["asset"]] = a["key"]
    remaining = list(acts)
    while remaining:
        progressed = False
        for a in list(remaining):
            if all(i in produced for i in a["inputs"]) and (prev[a["key"]] is None or prev[a["key"]] in times):
                start = max([produced[i] for i in a["inputs"]] + ([times[prev[a["key"]]][1]] if prev[a["key"]] else []) or [0.0])
                end = start + sample(a["dist"], rng)
                times[a["key"]] = (start, end)
                produced[a["output"]] = end
                remaining.remove(a)
                progressed = True
        if not progressed:
            raise RuntimeError("deadlock: " + ", ".join(a["num"] for a in remaining))
    return times


def metrics(times):
    """The numbers read from one run. All in seconds."""
    t = times
    end_all = max(e for _, e in t.values())
    return {
        "completion": end_all,
        # requirement 2.1.1 / 3.4.2.2: from opening the planner to the end of "submit"
        "entry": t["submit"][1] - t["open"][0],
        # requirement 2.1.2 / 3.4.2.1, plan page: end of submit to the comparison displayed
        "response_plan": t["present"][1] - t["submit"][1],
        # same requirement, result page: end of "choose" to the trip result displayed
        "response_result": t["display"][1] - t["choose"][1],
        # component requirement 5.5.3: validated entry to factor record and trip forecast returned
        "refdata": max(t["factor"][1], t["resolve"][1]) - t["validate"][1],
        # component requirement 5.5.3 (second half) and 5.4.4: the Open-Meteo call itself
        "openmeteo_call": t["wx"][1] - t["wx"][0],
        # the system side of the plan page, without the commuter's own actions
        "system_plan": t["present"][1] - t["validate"][0],
    }


def utilization(times, acts, total):
    """Share of the run during which each asset has at least one action running (union of intervals)."""
    by_asset = {}
    for a in acts:
        by_asset.setdefault(a["asset"], []).append(times[a["key"]])
    out = {}
    for asset, spans in by_asset.items():
        spans.sort()
        busy, cur_s, cur_e = 0.0, None, None
        for s, e in spans:
            if cur_e is None or s > cur_e:
                if cur_e is not None:
                    busy += cur_e - cur_s
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        busy += cur_e - cur_s
        out[asset] = busy / total if total else 0.0
    return out


def run_many(sc, n, seed):
    rng = np.random.default_rng(seed)
    acts = S.actions(sc)
    rows = []
    for _ in range(n):
        tm = run_once(sc, rng, acts)
        m = metrics(tm)
        m["util"] = utilization(tm, acts, m["completion"])
        m["times"] = tm
        rows.append(m)
    return rows


def summary(values):
    v = np.asarray(values, float)
    return {"min": float(v.min()), "max": float(v.max()), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
            "p50": float(np.percentile(v, 50)), "p95": float(np.percentile(v, 95))}
