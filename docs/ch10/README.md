# Chapter 10: Modeling and Simulation

The report is `EcoCommute_Team6_Ch10_Modeling_and_Simulation.docx` (and `.pdf`). Everything else in this folder is what it
was made from, so the numbers can be reproduced.

| Folder | Content |
|---|---|
| `sim/` | `scenarios.py` (the two scenarios, durations and their rationale: single source), `engine.py` (Monte Carlo and discrete-event engine), `run_simulation.py`, `draw.py` (diagrams), `analysis.py` (summaries and charts) |
| `instrument/` | `measure_uc3.py`: the instrumentation harness that times every participant boundary of the real web application |
| `data/` | Simulation runs, measured runs and spans, `analysis.json`; `earlier_campaign_2026-11-15/` is a first measurement campaign cut short by the routing quota |
| `diagrams/` | Redrawn action diagrams, sequence diagrams and charts |
| `innoslate/` | Innoslate screenshots and Monte Carlo exports, and the steps to import and run the model (`README.md`) |
| `build/` | `build_report.py` and `measured_text.py` (the report text, generated from the data) |

The Innoslate import file is `docs/model/EcoCommute_11.4_C10_simulation.xml` (`docs/model/scripts/build_model_11_4.py`).

**The committed `.docx` was adjusted by hand in Word** (page orientation and picture sizes). `build/build_report.py` regenerates
the report with its own layout, so run it to a different file name, not over the committed report, or the manual layout is lost.

The measurement needs Flask (`pip install -r requirements.txt`) and an `ORS_API_KEY`; the free routing plan allows 200 requests a
day and each measured run uses three.
