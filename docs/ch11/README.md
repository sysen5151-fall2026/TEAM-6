# Chapters 11 and 12: System Analysis and Risk Assessment

The report is `EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx` (and `.pdf`). Everything else in this
folder is what it was made from, so the numbers can be reproduced.

| Folder | Content |
|---|---|
| `spike/` | The live measurements: `measure_phases.py` (where a new connection spends its time), `measure_idle.py` (idle survival of a kept-open connection), `measure_dispatch.py` (the plan path under alternatives A to D), `validate_final.py` (the product after the change against the product before), `measure_c4.py` (the explanation-model spike) |
| `data/` | The measured files and `analysis.json`, the single source of the report's numbers; `test_run.json` is the last full test run |
| `sim/` | `model.py` (criteria, value functions, swing weights, scores, sensitivity, life cycle cost, risk ratings: the team's judgments sit here), `figures.py` |
| `build/` | `build_report.py`, `make_risks_md.py` (writes `docs/risks.md`), `make_adr.py` (writes ADR 0012) |
| `diagrams/` | The figures of the report |
| `innoslate/` | Put the Innoslate screenshots of model 11.5 here (`risk_matrix.png` replaces the redrawn matrix in the report) |

Order: spikes -> `sim/model.py` -> `sim/figures.py` -> `build/make_risks_md.py`, `build/make_adr.py` -> `docs/model/scripts/build_model_11_5.py` -> `build/build_report.py`.

The decision is recorded in [ADR 0012](../adr/0012-plan-path-dispatch.md) and [ADR 0011](../adr/0011-c4-model-behind-a-guardrail.md); the risks in
[docs/risks.md](../risks.md); the model import is `docs/model/EcoCommute_11.5_C11-C12_analysis_risk.xml`.

Measured on one laptop on 22 November 2026; the `measure_dispatch.py gap` runs replace the routing directions call by a no-quota request
to the same host (see its docstring). The report says which numbers are measured, counted, assumed or replayed.

**The committed `.docx` is rebuilt by `build_report.py`; if the team adjusts its layout by hand in Word, build to another file name.**
