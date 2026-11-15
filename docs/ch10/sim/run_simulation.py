"""Run the simulations and write docs/ch10/data/sim_results.json and the raw run files.

    python docs/ch10/sim/run_simulation.py

Settings (also stated in the report, Section 4.1):
  Discrete-event table: 10 runs per scenario, NumPy default_rng seed 5151 (SC.1) and 5152 (SC.2).
  Monte Carlo: 1000 runs per scenario, seeds 20261115 and 20261116.
"""
import csv
import json
import os

import numpy as np

import engine as E
import scenarios as S

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)
DES_SEED = {1: 5151, 2: 5152}
MC_SEED = {1: 20261115, 2: 20261116}
N_DES, N_MC = 10, 1000
KEYS = ["completion", "entry", "response_plan", "response_result", "refdata", "openmeteo_call", "system_plan"]
THRESH = {"entry": 30.0, "response_plan": 3.0, "response_result": 3.0, "refdata": 1.2, "openmeteo_call": 1.0}


def main():
    res = {"des": {}, "mc": {}, "settings": {"n_des": N_DES, "n_mc": N_MC, "des_seed": DES_SEED, "mc_seed": MC_SEED}}
    for sc in (1, 2):
        des = E.run_many(sc, N_DES, DES_SEED[sc])
        res["des"][sc] = [{k: r[k] for k in KEYS} for r in des]
        mc = E.run_many(sc, N_MC, MC_SEED[sc])
        block = {k: E.summary([r[k] for r in mc]) for k in KEYS}
        block["prob"] = {k: float(np.mean([r[k] <= t for r in mc])) for k, t in THRESH.items()}
        assets = [a for a, _, _ in S.ASSETS]
        block["util"] = {a: float(np.mean([r["util"].get(a, 0.0) for r in mc])) for a in assets}
        # mean busy seconds per asset (utilization x completion)
        block["busy_s"] = {a: float(np.mean([r["util"].get(a, 0.0) * r["completion"] for r in mc])) for a in assets}
        block["action_mean"] = {k: float(np.mean([r["times"][k][1] - r["times"][k][0] for r in mc])) for k in mc[0]["times"]}
        block["finish_mean"] = {k: float(np.mean([r["times"][k][1] for r in mc])) for k in mc[0]["times"]}
        # which of X.6 and X.3 ends last in SC.2 (the critical branch), as a share of runs
        block["route_last"] = float(np.mean([r["times"]["route"][1] >= r["times"]["wx"][1] for r in mc]))
        res["mc"][sc] = block
        with open(os.path.join(DATA, f"sim_sc{sc}_mc_runs.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["run"] + KEYS)
            for i, r in enumerate(mc, 1):
                w.writerow([i] + [f"{r[k]:.4f}" for k in KEYS])
    # paired difference on the same random draws is not needed: the two sets use different seeds, so report both
    with open(os.path.join(DATA, "sim_results.json"), "w") as f:
        json.dump(res, f, indent=1)
    for sc in (1, 2):
        b = res["mc"][sc]
        print(f"SC.{sc}", {k: round(b[k]["mean"], 3) for k in KEYS}, {k: round(v, 3) for k, v in b["prob"].items()})
        print("   util", {k: round(v, 3) for k, v in b["util"].items()})
    print("route last in SC.2:", round(res["mc"][2]["route_last"], 3))


if __name__ == "__main__":
    main()
