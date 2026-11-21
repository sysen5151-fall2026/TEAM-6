# Innoslate screenshots for model 11.5

The model is `docs/model/EcoCommute_11.5_C11-C12_analysis_risk.xml` (built by `docs/model/scripts/build_model_11_5.py`; structure checked by
`tests/test_model_11_5.py`; imported into the team's Innoslate project on 22 November 2026: Intelligence pass rate 74%, warnings only, no errors).

1. Import it into a new project (as for 11.0 and 11.4), then open Intelligence and record the result (the new entities are Statements EC.1 to EC.6
   and DEC.1, Assets AL.A to AL.E, Risks TR.16 to TR.22, and new Probability and Consequence on the existing risks).
2. Save these screenshots here (the report picks up `risk_matrix.png` in place of its redrawn matrix; add the others as figures if wanted):
   - `risk_matrix.png`: Risk Matrix view of the Risk class (five table risks TR.16, TR.11, TR.10, TR.4, TR.1 are the ones the report discusses; the others are the register).
   - `risk_table.png`: the Risk table view with Probability, Consequence and Description.
   - `criteria.png`: the Statements EC.1 to EC.6 and DEC.1 with their relations.
   - `alternatives.png`: Assets AL.A to AL.E related to C.0.2 and C.0.6.
   - `intelligence_11_5.png`: the Intelligence report.
3. Rebuild the report: `python docs/ch11/build/build_report.py` (then update the table of contents in Word).
