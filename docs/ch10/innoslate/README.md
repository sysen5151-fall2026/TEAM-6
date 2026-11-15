# Innoslate steps for the Chapter 10 report

Everything in `docs/ch10/diagrams/` is drawn from `docs/ch10/sim/scenarios.py`, the same data that the import file
`docs/model/EcoCommute_11.4_C10_simulation.xml` is built from. The report builder uses a screenshot from this folder
instead of the drawn figure when a file with the name below exists, so the report can show the real Innoslate
diagrams without any edit to the text. Run `python docs/ch10/build/build_report.py` afterwards.

## 1. Import (about 5 minutes)

Import `docs/model/EcoCommute_11.4_C10_simulation.xml` into a new project (an earlier version of this file was
imported once: delete that project or its `SIM.1`, `SIM.2` and `t.*` entities first). It is model 11.3 plus 44
entities: parent actions `SIM.1` and `SIM.2`, their 36 actions `t.1.1`-`t.1.18` and `t.2.1`-`t.2.18`, six new
input/outputs, and `satisfies` links. Each action already has its duration distribution (Normal mu, sigma; Exponential
lambda; seconds), every received input/output is a trigger, and each scenario is a parallel group with one branch per
performing asset (the same structure as `UC.1`). The first version imported without errors (Intelligence 71 percent,
then 74 percent with warnings only); read the Intelligence report of this version.

Open `SIM.1` and `SIM.2`, then their **Action Diagram**. SC.2 differs from SC.1 only in which input/output triggers
which action: the weather request (`t.2.7`) and the factor lookup (`t.2.10`) follow the route request (`t.2.6`) at once,
so the Route Service and Open-Meteo branches answer side by side.

## 2. Simulate and capture

Action Diagram toolbar, **Simulate**, **Monte Carlo**: at least 100 iterations (default 100; the report's own runs are
1000). Capture the result window (status with the average duration, time bar chart, asset utilization). Save here:

| File | Content |
|---|---|
| `ad_sc1.png`, `ad_sc2.png` | Action diagram of SC.1 and SC.2, one branch per asset, legible (arrange the boxes so none overlap) |
| `sq_sc1.png`, `sq_sc2.png` | Sequence diagram generated from each action diagram |
| `mc_sc1.png`, `mc_sc2.png` | Monte Carlo result window for each scenario |

Compare Innoslate's average completion time with the Monte Carlo table of the report, Section 5.3 (the means should agree
within sampling error). If they do not, check the distributions first.
