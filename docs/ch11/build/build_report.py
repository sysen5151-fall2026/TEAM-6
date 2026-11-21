"""Builds EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx from docs/ch11/data and the model.

    python docs/ch11/build/build_report.py [output.docx]

Run order: spikes (docs/ch11/spike) -> docs/ch11/sim/model.py -> docs/ch11/sim/figures.py -> this script.
Two passes so that cross-references to figures and tables are numbered. Every number in the text comes from analysis.json
and the CSV files in docs/ch11/data. The default output is the file named above in docs/ch11.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report_lib as R  # noqa: E402  (puts the helper folders on the path)
import docx_helpers as H  # noqa: E402
from report_lib import A, F, NAMES, SEL, T, cap_tab  # noqa: E402
import sec_analysis as SA  # noqa: E402
import sec_risk as SR  # noqa: E402
from docx.shared import Pt, RGBColor  # noqa: E402

OUT = os.path.join(R.ROOT, "docs", "ch11", "EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx")

TEAM = [
    ("Luyu Chen", "Project Manager and Integration Lead", "Integrated the report; owned the product build and the review of the code, tests and ADRs (alternative selected, guardrails); model 11.5 import; branch and merge."),
    ("Mingjie Fang", "Quality, Risk and Documentation Lead", "Risk identification from the IDEF0 interactions; risk table, scales and calculation method; risk matrix; monitoring plan; risk register review; assessment-criteria check (Appendix B)."),
    ("Karen Li", "Product and Stakeholder Lead", "Evaluation criteria and their traces to stakeholder needs; importance ratings of the swing weight matrix; customer-value reasoning for the five alternatives."),
    ("Yinping Yin", "Sustainability Data and Analysis Lead", "Data collection and source verification (Open-Meteo and routing limits, licences); life cycle cost and affordability analysis; review of the measurements."),
    ("Yiyang Zou", "Technical Architecture Lead", "Physical architecture alternatives and their model entities AL.A to AL.E; dispatch and name-cache design; deployed-host measurement (open action); Innoslate screenshots."),
]


def front(d):
    for text, size, bold in [("SYSEN 5151 Foundations of Systems Engineering", 11, False), ("EcoCommute (Team 6)", 20, True), ("Systems Analysis and Risk Assessment", 24, True),
                             ("A swing weight trade-off on the plan path with the selected alternative built, and a risk assessment with a guardrail and a fallback built and tested (Chapters 11 and 12)", 12, False),
                             ("Report section for Project Task 6, Design Definition", 10.5, False),
                             ("Innoslate model: EcoCommute 11.5 (11.4 plus the criteria, alternatives and decision of Chapter 11 and the risks of Chapter 12)   |   November 2026", 9.5, False)]:
        p = d.add_paragraph()
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
        if size >= 20:
            r.font.color.rgb = H.NAVY
        p.paragraph_format.space_after = Pt(4)
    H.heading(d, "Team Contribution", 1)
    H.para(d, "The table lists who contributed which part of this assignment. Roles come from the team charter in the repository README. The assignment of parts was drafted from the roles and is to be confirmed by the team before submission.")
    H.table(d, ["Team member", "Role", "Contribution to Chapters 11 and 12"], TEAM, [1.2, 1.9, 4.0], size=9)
    p = d.add_paragraph()
    r = p.add_run("Table of Contents")
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = H.NAVY
    p = d.add_paragraph()
    H.add_field(p, 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")
    d.add_page_break()


def traceability(d):
    H.heading(d, "11 Model Traceability", 1)
    H.para(d, "Model 11.5 (docs/model/EcoCommute_11.5_C11-C12_analysis_risk.xml, built by docs/model/scripts/build_model_11_5.py from model 11.4) adds the entities below and changes nothing that was there except the Probability and Consequence of the existing risks. "
              "The criteria, alternatives and decision are the model authorizations that Chapter 11 requires before the build; the risks and their ratings are those that Chapter 12 requires before the guardrail.")
    cap_tab(d, "trace", "Entities added to the model and what each relates to.")
    rows = [
        ("EC.1 to EC.6 (Statements)", "Evaluation criteria with metric, range, value function, importance, swing weight", "Traced to requirements 2.1.2, 3.4.2.1, 5.5.3, 3.4.1.2, 3.4.4.1, 5.5.5, 2.3.1 and to needs 1.1.1, 1.3.2, 1.1.7, 1.5.3, 1.2.3"),
        ("AL.A to AL.E (Assets)", "The five physical architecture alternatives", "Related to C.0.2 and C.0.6 and to each other; AL." + SEL + " satisfies 3.4.2.1"),
        ("DEC.1 (Statement)", "The decision: alternatives, scores, selection", "Related to AL.A to AL.E and EC.1 to EC.6"),
        ("TR.16 (Risk)", "External service answers late and the 3-second display fails", "Related to F.2.2.3, F.2.2.4, IO.5 and requirements 3.4.2.1, 5.4.4, 5.5.3"),
        ("TR.17 to TR.22 (Risks)", "The AI-specific risks of the register", "Related to C.4 (TR.17 to TR.20), UC.3.5 and requirements 2.1.10, 2.5.1, 3.4.5.2, 2.3.1"),
        ("TR.1, TR.4, TR.7, TR.10, TR.11, TR.13 to TR.15 (existing Risks)", "Probability and Consequence set from the register ratings", "TR.4 and TR.11 also related to the actions they come from"),
    ]
    H.table(d, ["Entity", "Content", "Relations"], rows, [1.7, 2.7, 2.7], size=8.5)
    H.para(d, "Model 11.5 was checked by script for well-formed XML and relation integrity (tests/test_model_11_5.py) and then imported into the team's Innoslate project (Cornell Systems Engineering, EcoCommute_11.5_C11-C12_analysis_risk). "
              "The Intelligence dashboard (" + F("intel") + ") analysed 460 entities with an overall pass rate of 74%: it reports warnings only and no errors. The warnings are the usual ones for entities that have no relation to another entity yet "
              "or whose names are similar, and the model-wide figure is close to that of the earlier imports (77% for model 11.0). The risk matrix of Section 7 is the Innoslate Risk Diagram of the same project.")
    R.fig(d, "intel", "intelligence_11_5.png", "Innoslate Intelligence dashboard for model 11.5 (460 entities, pass rate 74%, warnings only).", 6.4, shot="intelligence_11_5.png")


def summary(d):
    H.heading(d, "12 Summary and Next Steps", 1)
    for t in [
        f"The open decision was how the plan path asks the external services. Five alternatives were described, modeled and measured or replayed; alternative {SEL}, {NAMES[SEL].lower()}, was selected (score {SA.f1(SA.TOT[SEL]['score'])}; the order is " + ", ".join(f"{k} {SA.f1(SA.TOT[k]['score'])}" for k in SA.RANK) + "), and it is built.",
        "The measurements changed the diagnosis: the slow new connection of Chapter 10 is a host-name lookup (3.05 to 3.09 s in 21 of 24 trials on the development laptop), not connection set-up. The routing service's refusal stopped one campaign; it was recorded and worked around, not hidden.",
        f"The top risk, {SR.TOP['id']}, is the risk the decision reduces. It is handled by mitigation: parallel calls, the selected mechanism, deadlines of 1.0 s and 1.2 s with a labelled fallback, and the indicators and review points of Section 9.",
        "The register has 15 risks, seven of them AI-specific; a guardrail or fallback exists for each AI-specific risk that can be controlled by the team, and tests that try to get past them pass. A small local model got the facts wrong in 20 of 40 cases and none reached the page.",
        "Open: (1) review and approve the merge; (2) measure on the deployed host with at least 30 cold runs (Chapter 10 decision D9); (3) check the Chapter 10 figure of 200 routing requests a day against the provider's dashboard (the published limit is 2,000 a day and 40 a minute); (4) inspect 50 explanations before the model is ever switched on.",
    ]:
        H.bullet(d, t)


def appendices(d):
    H.heading(d, "Appendix A Reproducing the work", 1)
    for line in [
        "Spike 1b: python docs/ch11/spike/measure_phases.py api.open-meteo.com 12 10 (and api.openrouteservice.org), docs/ch11/spike/measure_idle.py",
        "Spike 2: PROXY_ROUTES=1 python docs/ch11/spike/measure_dispatch.py gap A 8 120 (B, C, D likewise); python docs/ch11/spike/measure_dispatch.py warm 8 8 (needs ORS_API_KEY)",
        "Spike 3 (explanation model, Section 10): ollama serve, ollama pull qwen2.5:1.5b, python docs/ch11/spike/measure_c4.py --label gpu",
        "Analysis and figures: python docs/ch11/sim/model.py; python docs/ch11/sim/figures.py; python docs/ch11/build/make_risks_md.py",
        "Model: python docs/model/scripts/build_model_11_5.py; this report: python docs/ch11/build/build_report.py",
        "Tests: python -m unittest discover -s tests -t . (Flask installed for the web tests)",
    ]:
        H.bullet(d, line, size=9.5)
    H.heading(d, "Appendix B Check against the assessment criteria", 1)
    H.para(d, "The lab manual's Risk Assessment Criteria and the rubric of the assignment, item by item.")
    cap_tab(d, "check", "Criteria and where each is met.")
    rows = [
        ("Project report: integrated, standard form, justified structure", "Sections 1 to 12; the storyline from Chapter 10 to the top risk is in Section 1.2 and Section 12"),
        ("Scope, criteria, objective functions", "Sections 2.1 and 2.3; " + T("criteria") + " (trace to needs, requirements, model entities; units and ranges)"),
        ("Physical architecture alternatives, genuinely open, at least two, in the model", "Section 1.2 (why open), 2.2 (five alternatives, what each requires), model entities AL.A to AL.E (Section 11)"),
        ("Swing weight matrix, value scores, effectiveness, LCC, affordability, sourced, assumptions", "Sections 3 and 4; " + T("matrix") + " to " + T("lcc") + "; sources and assumptions in Section 3.3"),
        ("Selection follows from results; sensitivity; implemented and merged; decision record", "Section 5; ADR 0012; code in Section 5.3 (merge pending the team's approval)"),
        ("Three to five system-level risks from the architecture model; description with type and phase; required columns; scales; calculation", "Section 6 (" + T("risktable") + " and " + T("scales") + ")"),
        ("Risks plotted correctly on the risk matrix, described", "Section 7"),
        ("Top risk selected from table and matrix; strategy stated and justified; specific plan traced to model entities", "Section 8 (separate page; " + T("plan") + ")"),
        ("Monitoring early in the life cycle, indicators, review points, use of the modeling tool", "Section 9"),
        ("Product risk register with conventional and AI-specific risks, cross-referenced; guardrail or fallback; failure-path test passes; own ratings", "Section 10; docs/risks.md; tests/test_c4_guardrail.py and tests/test_dispatch_guardrail.py"),
        ("Team contribution table", "First page"),
    ]
    H.table(d, ["Criterion", "Where"], rows, [3.4, 3.7], size=8.5)
    H.heading(d, "Appendix C Sources", 1)
    for s in [
        "Open-Meteo, Terms of Use and Pricing (free API limits): https://open-meteo.com/en/terms ; https://open-meteo.com/en/pricing (read 22 November 2026).",
        "OpenRouteService, frequently asked questions (directions limits 2,000 a day, 40 a minute; 403 and 429 answers): https://giscience.github.io/openrouteservice/frequently-asked-questions (22 November 2026; the Chapter 10 report's figure of 200 a day conflicts, see Section 3.1).",
        "Ollama library, qwen2.5:1.5b (licence Apache 2.0, 986 MB): https://ollama.com/library/qwen2.5:1.5b (22 November 2026).",
        "Foundations of Systems Engineering Lab Manual, Version 3.0, Chapters 11 and 12.",
        "EcoCommute Team 6: Chapter 8 and 9 report (apportionment of cost and time), Chapter 10 report (measured and simulated stages), docs/prompt-log.md, docs/adr/0003, 0010, 0011 and 0012.",
    ]:
        H.bullet(d, s, size=9.5)


def build(path):
    R.reset_counters()
    d = H.new_document()
    front(d)
    SA.intro(d)
    SA.prepare(d)
    SA.data(d)
    SA.value(d)
    SA.selection(d)
    SR.risk_ident(d)
    SR.risk_matrix(d)
    SR.top_risk(d)
    SR.monitoring(d)
    SR.register(d)
    traceability(d)
    summary(d)
    appendices(d)
    H.header_footer(d, "EcoCommute Team 6 | Systems Analysis and Risk Assessment (Chapters 11 and 12)")
    d.save(path)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else OUT
    build(path)      # first pass numbers the figures and tables
    build(path)      # second pass resolves the references
    print("wrote", path)
