"""Builds EcoCommute_Team6_Ch8-Ch9_Architecture_Definition_Form.docx (two passes so cross-references are numbered)."""
import os
import sys
import mdata as M
import pdata as P
import reqdata as Q
from docx_helpers import *
from docx.shared import Pt, Inches

HERE = os.path.dirname(os.path.abspath(__file__))
DIA = os.path.join(HERE, "..", "diagrams")
OLD = os.path.join(HERE, "..", "..", "ch6-ch7", "diagrams")
OUT = os.path.join(HERE, "..", "EcoCommute_Team6_Ch8-Ch9_Architecture_Definition_Form.docx")
SHOTDIR = os.path.join(HERE, "..", "innoslate")
# figure key -> file name of the Innoslate screenshot that replaces the rendered figure when it exists
SHOTS = {"idef1": "idef0_first.png", "idef2": "idef0_second.png", "hier": "hier_overall.png", "hier0": "hier_universe.png",
         "meta": "metafunction_idef0.png", "hier1": "hier_c0.png", "hier2": "hier_c02.png", "ctx": "asset_context.png", "asset1": "asset_first.png",
         "i2a": "i2_first.png", "i2b": "i2_second.png", "n2b": "n2_second.png", "spider": "spider_c02.png"}
NUM = {"fig": {}, "tab": {}}
REG = {"fig": [], "tab": []}


def F(k):
    return f"Figure {NUM['fig'].get(k, '?')}"


def T(k):
    return f"Table {NUM['tab'].get(k, '?')}"


def nw(n):
    w = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    return w[n] if n < len(w) else str(n)


def cap(t):
    return t[0].upper() + t[1:]


def model_counts():
    """Leaf requirement counts of the system requirements document (3) in the model export."""
    import re as _re
    from lxml import etree
    p = os.path.join(HERE, "..", "..", "model", "EcoCommute_11.3_C8-C9_physical_architecture.xml")
    r = etree.parse(p).getroot()
    nums = [e.findtext("number") for e in r.find("database").findall("entity") if (e.findtext("number") or "").startswith("3.")]
    nums = [n for n in nums if _re.fullmatch(r"3(\.\d+)+", n)]
    leaf = [n for n in nums if not any(m.startswith(n + ".") for m in nums)]
    grp = {"3.1.1": 0, "3.1.2": 0, "3.2": 0, "3.3": 0, "3.4": 0}
    for n in leaf:
        for g in grp:
            if n.startswith(g + "."):
                grp[g] += 1
                break
    return grp


def build():
    REG["fig"].clear()
    REG["tab"].clear()
    d = new_document()

    def fig(key, path, width, text):
        REG["fig"].append(key)
        shot = SHOTS.get(key)
        if shot and os.path.exists(os.path.join(SHOTDIR, shot)):
            path = os.path.join(SHOTDIR, shot)
        picture(d, path, width)
        caption(d, f"Figure {len(REG['fig'])}. {text}")

    def tab(key, text, header, rows, widths, **kw):
        REG["tab"].append(key)
        c = caption(d, f"Table {len(REG['tab'])}. {text}")
        c.paragraph_format.keep_with_next = True
        return table(d, header, rows, widths, **kw)

    def landscape():
        new_section(d, True)

    def portrait():
        new_section(d, False)

    io = lambda k: f"{k} {P.IO_ALL[k]}"
    A = P.ASSET_NAME

    # ============================================================ title
    for txt, sz, b in [("SYSEN 5151 Foundations of Systems Engineering", 12, False), ("EcoCommute (Team 6)", 22, True),
                       ("Architecture Definition: Form (Physical Architecture)", 18, True),
                       ("First-Level Form Architecture (Chapter 8) and Second-Level Form Architecture and Component Specification (Chapter 9)", 13, False),
                       ("Report section combining the Chapter 8 and Chapter 9 assignments", 10.5, False),
                       ("Innoslate model: EcoCommute 11.3 (11.0 plus the physical architecture of this section)   |   October 2026", 9.5, False)]:
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(txt)
        r.font.size = Pt(sz)
        r.bold = b
        if b:
            r.font.color.rgb = NAVY
    heading(d, "Team Contribution", 1)
    para(d, "The table lists who contributed which part of this assignment. Roles come from the team charter in the repository README.")
    table(d, ["Team member", "Role", "Contribution to Chapters 8 and 9"], [
        ["Luyu Chen", "Project Manager and Integration Lead", "Integrated the report and the Innoslate model (EcoCommute 11.3); Section 3 requirements traceability and spider diagram; consistency check of every figure, table and identifier across the report."],
        ["Mingjie Fang", "Quality, Risk and Documentation Lead", "Architecture evaluation against the functional architecture (Section 2.3) and the assessment-criteria checks (Appendix A); report editing."],
        ["Karen Li", "Product and Stakeholder Lead", "Choice of the decomposed function and its complexity analysis (Section 2.1.1.3); non-functional considerations (Section 2.2.1.3); alternative physical architectures and their evaluation (Section 2.4)."],
        ["Yinping Yin", "Sustainability Data and Analysis Lead", "System design output requirements and the Reference Data Subsystem component specification, including MOPs, verification criteria and the apportionment budgets (Section 3.2)."],
        ["Yiyang Zou", "Technical Architecture Lead", "First-level and second-level IDEF0 with mechanisms, asset hierarchy and asset diagrams, N2 and I2 diagrams, sequence diagrams (Sections 2.1 and 2.2)."],
    ], [1.2, 1.7, 3.8], size=8.5, first_bold=True)
    para(d, "**Table of Contents**", size=13)
    toc = d.add_paragraph()
    add_field(toc, 'TOC \\o "1-5" \\h \\z \\u', "Right-click and choose Update Field to refresh the table of contents.")
    d.add_page_break()

    # ============================================================ 1 Introduction
    heading(d, "1 Introduction", 1)
    heading(d, "1.1 Purpose of Design Definition", 2)
    para(d, "Chapters 6 and 7 gave EcoCommute a function architecture that was traced against the operational concept. Design Definition asks the next question: what are the parts that perform these functions, how do they connect, and what must each part do and meet? Chapter 8 allocates each first-level function to a first-level physical asset (subsystem), draws the asset diagrams that show the interfaces between assets, and completes the system-level requirements. Chapter 9 repeats the step one level lower for the most complex first-level function: it decomposes the function, allocates the new functions to second-level assets (modules), writes a component specification, and flows the system-wide requirements down to the component.")
    para(d, "The result is a form (physical) architecture in which every function has exactly one performer, every input/output crosses a named interface, and every requirement can be given to a named asset. This is what a design team or supplier needs before building, and what the verification plan needs before testing.")
    heading(d, "1.2 Description of Design Definition", 2)
    para(d, "The system of interest is C.0 EcoCommute, a responsive web application that estimates commute CO2e and suggests feasible greener options; its external assets are X.1 Commuter, X.2 Pilot Administrator, X.3 Open-Meteo, X.4 Emission Factor Publisher and X.5 Hosting Provider; models 10.9 and 11.0 added X.6 Route Service and X.7 Transit Schedule Publisher for the trip planner. The work starts from Innoslate model 11.0 (the function architecture of Chapters 6 and 7, unchanged by 11.0: Metafunction, eight first-level functions F.2.0 to F.2.7 and 22 input/outputs; plus the use cases UC.3 and UC.4) and produces model 11.3. The export is stored with the report (docs/model/EcoCommute_11.3_C8-C9_physical_architecture.xml); Appendix B gives the model baseline and the source of every figure.")
    para(d, f"Section 2 presents the architecture: the functional architecture it rests on (2.1), the physical architecture with mechanisms, asset hierarchy and interfaces (2.2), its evaluation against the functional architecture (2.3) and the physical alternatives that were considered (2.4). Section 3 presents requirements management: traceability (3.1) and the system design output requirements, including the component specification and the flow-down of system-wide requirements (3.2). {T('items')} lists the assignment items and where each is covered.")
    tab("items", "Assignment items and where they are covered in this report.", ["Item", "Activity", "Source", "Section"], [
        ["First-level physical architecture", "Add mechanisms to the first-level IDEF0; create asset hierarchy diagrams", "Innoslate model 11.3", "2.2.1"],
        ["Asset diagrams", "Generate the context and first-level asset diagrams with transfers relationships", "Innoslate model 11.3", "2.2.2"],
        ["System-level specification", "Update system requirements; add system-wide requirements; trace them to C.0", "Innoslate model 11.3", "2.2.1.3, 3.1"],
        ["Second-level functional architecture", "Decompose F.2.2 Manage Reference Data into F.2.2.1 to F.2.2.4; allocate input/outputs", "Innoslate model 11.3", "2.1.1, 2.1.2"],
        ["Second-level physical architecture", "Add mechanisms C.0.2.1 to C.0.2.4; create asset hierarchy diagrams", "Innoslate model 11.3", "2.2.1"],
        ["Component specification", "Input, output, interface and functional requirements for C.0.2", "Innoslate model 11.3", "3.2.2"],
        ["System-wide flow-down", "Equivalence, apportionment or synthesis, with rationale", "Innoslate model 11.3", "3.2.2"],
        ["Physical interface", "Create I2 diagrams", "Innoslate model 11.3", "2.2.2.1"],
        ["Team contribution", "State which student did which part", "Team", "Front matter"],
    ], [1.7, 3.2, 1.2, 0.9], size=8.5)
    para(d, "**Assumptions and conventions.**", after=2)
    bullet(d, "Function names are verb phrases; asset and input/output names are noun phrases. Numbering: F.2.k for first-level functions, C.0.k for the subsystem that performs F.2.k, F.2.2.m for second-level functions and C.0.2.m for the module that performs F.2.2.m. The numbers mirror the hierarchy, so a function and its mechanism share their last digits. Input/outputs IO.1 to IO.22 are those of model 10.8; IO.23 and IO.24 are new.")
    bullet(d, "The one-to-one rule of the lab applies at every level: each function is performed by exactly one asset and each asset performs exactly one function. Where several hardware or software items serve one function, they are kept inside one aggregate subsystem and split at the next level.")
    bullet(d, "The four modules of the Chapter 2 walking skeleton (C.1 Web Front End, C.2 Application Service, C.3 Data Adapter, C.4 Explanation Model) are a code view. They cross function boundaries, so they are not the first-level form architecture. They are kept in the model, detached from C.0, and allocated to the new subsystems in Section 2.2.1.1 and evaluated as Alternative B in Section 2.4.")
    bullet(d, "Budgets and dates in the flow-down (cost shares, response-time shares, availability shares, the integration date) are educated guesses, as the lab allows. Each is stated with its rationale and a recommendation for detailed analysis.")
    bullet(d, "The first-level N2 diagram and the action diagram come from the Chapter 6 and 7 report (model 10.8) and are reused unchanged. Every diagram of the new architecture is an Innoslate screenshot of the model, except the two sequence diagrams, which Innoslate cannot draw with internal interactions, and any figure marked in Appendix B as drawn from the model data.")

    # ============================================================ 2 Architecture Definition
    heading(d, "2 Architecture Definition", 1)
    heading(d, "2.1 Functional Architecture", 2)
    para(d, "The form architecture is allocated from the functional architecture, so this section recalls the first level from Chapter 7 and adds the second level that Chapter 9 requires.")
    heading(d, "2.1.1 Functional Architecture Model", 3)
    heading(d, "2.1.1.1 Function Elements", 4)
    para(d, f"The model has functions on three levels: the Metafunction F.0 with its six top-level functions F.1 to F.6; the eight first-level functions F.2.0 to F.2.7 that decompose F.2; and the four second-level functions F.2.2.1 to F.2.2.4 that decompose F.2.2. {T('funcs')} lists them with the asset that performs each. All functions are leaf nodes except F.0, F.2 and F.2.2.")
    rows = [["F.0", "Metafunction", "Universe", "Holds the top-level functions of the system of interest and of every external asset."]]
    for f, n in M.TOP.items():
        rows.append([f, n, f"{P.TOP_MECH[f]} {A[P.TOP_MECH[f]]}", "Top level." if f != "F.2" else "Decomposed into F.2.0 to F.2.7."])
    for f, n in M.L1:
        aid = P.FOR_FUNC[f]
        rows.append([f, n, f"{aid} {A[aid]}", "Decomposed into F.2.2.1 to F.2.2.4." if f == "F.2.2" else "Leaf function."])
    for f, v in P.FUNC2.items():
        rows.append([f, v[0], f"{v[1]} {v[2]}", "Leaf function."])
    tab("funcs", "Function elements and the asset that performs each (model 11.3).", ["ID", "Function", "Performed by (mechanism)", "Note"], rows, [0.7, 2.2, 2.4, 1.7], size=8)
    heading(d, "2.1.1.2 ICOM Summary for the First-Level and Second-Level Models", 4)
    para(d, f"{T('icom1')} summarises the inputs, controls, outputs and mechanism (ICOM) of each first-level function, taken from the first-level IDEF0 of model 10.8 and completed with the mechanism that this chapter allocates. {T('icom2')} does the same for the second-level functions. All 11 input/outputs of the Metafunction appear at the first level, and all six first-level flows of F.2.2 appear at the second level, so no input, control or output arrow is tunneled or left unconnected.")
    rows = []
    for f, n in M.L1:
        I_, C_, O_ = [], [], []
        for k, (srcs, dests) in M.L1FLOW.items():
            for dd, role in dests:
                if dd == f:
                    (I_ if role == "I" else C_).append(k)
            if f in srcs:
                O_.append(k)
        key = lambda x: int(x.split(".")[1])
        rows.append([f"{f} {n}", ", ".join(sorted(I_, key=key)), ", ".join(sorted(C_, key=key)), ", ".join(sorted(O_, key=key)), f"{P.FOR_FUNC[f]} {A[P.FOR_FUNC[f]]}"])
    tab("icom1", f"ICOM of the first-level functions (input/output numbers; names in {T('ios')}).", ["Function", "Inputs", "Controls", "Outputs", "Mechanism"], rows, [1.8, 1.0, 1.1, 1.3, 1.8], size=8)
    rows = []
    for f, v in P.FUNC2.items():
        I_, C_, O_ = [], [], []
        for k, (srcs, dests) in P.L2FLOW.items():
            for dd, role in dests:
                if dd == f:
                    (I_ if role == "I" else C_).append(k)
            if f in srcs:
                O_.append(k)
        key = lambda x: int(x.split(".")[1])
        rows.append([f"{f} {v[0]}", ", ".join(sorted(I_, key=key)) or "none", ", ".join(sorted(C_, key=key)) or "none", ", ".join(sorted(O_, key=key)), f"{v[1]} {v[2]}"])
    tab("icom2", "ICOM of the second-level functions of F.2.2. IO.23 and IO.24 are new internal input/outputs.", ["Function", "Inputs", "Controls", "Outputs", "Mechanism"], rows, [1.8, 1.0, 1.1, 1.3, 1.8], size=8)
    para(d, "F.2.2.1 has a control and no input because the reviewed factors govern what the store may hold and nothing is transformed; F.2.2.3 has an input and no control because its behaviour is fixed by interface requirement 3.2.3, a constraint rather than a flow. Both are valid IDEF0 and each function still has an input or a control, an output and a mechanism.")
    heading(d, "2.1.1.3 Choice of the Function to Decompose", 4)
    para(d, f"The lab asks the team to decompose its most complex first-level function. {T('cplx')} scores each first-level function by the number of distinct input/outputs it touches, the number of first-level functions and external assets it exchanges information with, and the number of its interactions in the baseline sequence of UC.1 (14 interactions). The score is a simple sum so that every term can be checked in the model.")
    tab("cplx", "Complexity of the first-level functions.", ["Function", "Input/outputs", "Internal partners", "External assets", "UC.1 interactions", "Score"],
        [[f"{r[0]} {r[1]}", r[2], r[3], r[4], r[5], f"**{r[6]}**" if r[6] == 17 else r[6]] for r in P.complexity()], [2.4, 0.9, 0.9, 0.9, 1.0, 0.6], size=8.5)
    para(d, "F.2.2 Manage Reference Data scores highest (17), narrowly ahead of F.2.4 Manage Commute Records (16). It is the only first-level function that exchanges information with two external assets (Open-Meteo and the Emission Factor Publisher), it takes part in six of the 14 interactions of the baseline scenario, and it feeds three other functions. F.2.4 has more input/outputs, but several of them are controls from the operational and retirement behaviour outside UC.1, so it exercises the baseline scenario less. F.2.2 also gives the component specification external interface requirements for two external systems, which is what the Chapter 9 criteria test.")
    heading(d, "2.1.1.4 Decomposition of F.2.2 into Second-Level Functions", 4)
    para(d, "F.2.2 holds reviewed emission factors, selects the applicable factor and obtains the forecast for the trip. It splits into four functions along two independent threads: the factor thread (load, then select) and the forecast thread (request, then resolve). The capabilities are:")
    for f, v in P.FUNC2.items():
        bullet(d, f"**{f} {v[0]}.** {v[3]}")
    para(d, f"The six input/outputs carried down from F.2.2 are allocated as follows: IO.6 (control) to F.2.2.1; IO.12 (input) to F.2.2.2 and F.2.2.3; IO.5 (input) to F.2.2.4; IO.14 from F.2.2.2, IO.4 from F.2.2.3 and IO.15 from F.2.2.4. Two internal flows are needed to complete the baseline use case: IO.23 Versioned Factor Set from F.2.2.1 to F.2.2.2 (a control that tells the selection which factors exist), and IO.24 Forecast Query Context from F.2.2.3 to F.2.2.4 (a control that tells the resolver which place and hour to pick out of the response). The two threads do not exchange information with each other, which is why the decomposition is cohesive. {T('plan3')} records the third-level decomposition planned for the final assignment, so that the most complex second-level function can be broken down once more.")
    tab("plan3", "Planned third-level decomposition (not modelled in this section).", ["Second-level function", "Planned third-level functions"],
        [[a, b] for a, b in Q.SECOND_LEVEL_PLAN], [2.6, 4.2], size=8.5)

    heading(d, "2.1.2 Functional Interface", 3)
    heading(d, "2.1.2.1 N2 Diagram", 4)
    para(d, f"{F('n2a')} is the N2 diagram of the first-level functions from model 10.8. The functions sit on the diagonal; a cell above or to the right of the diagonal holds the input/output that the function in its row sends to the function in its column; the top row holds what enters from outside and the right-hand column what leaves. {F('n2b')} is the N2 diagram of the four second-level functions: only two internal cells are filled (IO.23 and IO.24), which shows that the two threads are decoupled, and the top row and right-hand column hold the six boundary flows.")
    fig("n2a", os.path.join(OLD, "innoslate_n2.png"), 6.1, "N2 diagram of the first-level functions from Innoslate (model 10.8).")
    fig("n2b", os.path.join(DIA, "fig_n2_second.png"), 4.6, "N2 diagram of the second-level functions of F.2.2 (model 11.3).")
    heading(d, "2.1.2.2 Input/Output Elements", 4)
    rows = [[k, v, ("Metafunction" if int(k.split('.')[1]) <= 11 else "first level" if int(k.split('.')[1]) <= 22 else "second level (new)")]
            for k, v in sorted(P.IO_ALL.items(), key=lambda kv: int(kv[0].split('.')[1]))]
    tab("ios", "Input/outputs of the model. IO.1 to IO.11 are carried down from the Metafunction, IO.12 to IO.22 are first-level internal, IO.23 and IO.24 are second-level internal.", ["ID", "Name", "Level introduced"], rows, [0.8, 3.6, 2.0], size=8)

    heading(d, "2.1.3 Sequence of Operations", 3)
    heading(d, "2.1.3.1 Scenario Overview", 4)
    para(d, f"The scenario is the baseline use case UC.1, Review Commute Impact and Feasible Alternative: a Commuter with an account and consent opens the entry form, submits a valid trip, and receives the estimated CO2e, the difference from the always-drive baseline, the method disclosure, a feasible alternative and an explanation. It assumes suitable stored emission factors and an available forecast. The action diagram of UC.1 ({F('action')}) fixes the order of the six external input/outputs that the sequence must reproduce.")
    fig("action", os.path.join(OLD, "innoslate_action_diagram_numbered.png"), 5.6, "UC.1 action diagram from Innoslate with the external input/outputs numbered 2 to 7 in order of occurrence.")
    act = [("2", "Entry Request", "IO.1", "Found"), ("3", "Entry Form", "IO.3", "Found (F.2.1 added as a source of IO.3 in model 10.8)"),
           ("4", "Commute Request", "IO.1, IO.2", "Found"), ("5", "Weather Query", "IO.4", "Found (same flow, different name)"),
           ("6", "Weather Forecast", "IO.5", "Found (same flow, different name)"), ("7", "Commute Impact Result", "IO.3", "Found")]
    rows = []
    for n, nm_, ios, res in act:
        ends = []
        for k in ios.split(", "):
            sf, df, _ = M.META[k]
            ends.append(f"{k} {M.IO[k]}: {sf} > {df}")
        rows.append([n, nm_, "; ".join(ends), res])
    para(d, f"{T('actmap')} checks that every input/output of the action diagram is accounted for by an input/output of the Metafunction IDEF0. All six are; the seventh interaction of the scenario, Reviewed Emission Factors (IO.6), is a precondition that happens before the use case starts and is therefore not on the action diagram.")
    tab("actmap", "Input/outputs of the UC.1 action diagram and the Metafunction input/output that accounts for each.", ["Order", "Action diagram input/output", "Metafunction input/output and path", "Result"], rows, [0.5, 1.6, 3.4, 1.3], size=8.5)
    heading(d, "2.1.3.2 Detailed Sequence of Interactions", 4)
    para(d, f"{F('seq1')} replays UC.1 over the first-level assets. Each interaction is numbered once and named once; red interactions cross the system boundary and blue interactions are internal. {F('seq2')} zooms into the Reference Data Subsystem and replays the eight interactions of the scenario that cross or stay inside C.0.2. A flow that reaches several functions (IO.12 to four subsystems) is one interaction with several arrow heads.")
    fig("seq1", os.path.join(DIA, "fig_seq_first.png"), 7.0, "UC.1 sequence diagram over the first-level assets (model 11.3). Lifelines are the assets that perform the first-level functions.")
    fig("seq2", os.path.join(DIA, "fig_seq_second.png"), 7.0, "UC.1 sequence diagram over the second-level assets of C.0.2 (model 11.3).")
    heading(d, "2.1.3.3 Consistency with IDEF0 and the N2 Diagram", 4)
    rows = [[s[0], s[1], f"{s[2]} > {', '.join(s[3])}", s[4], s[5]] for s in P.SEQ1]
    tab("seqmap", "First-level sequence steps mapped to the IDEF0 flow and to the asset that sends and receives it. Every numbered step appears once.", ["Step", "Interaction", "Sender > receivers", "IO", "UC.1 action"], rows, [0.5, 2.2, 2.2, 0.6, 1.3], size=8)
    rows = [[s[0], s[1], f"{s[2]} > {', '.join(s[3])}", s[4], s[5]] for s in P.SEQ2]
    tab("seqmap2", "Second-level sequence steps for C.0.2. Step 2 reaches two modules because IO.12 is an input to F.2.2.2 and F.2.2.3.", ["Step", "Interaction", "Sender > receivers", "IO", "UC.1 action"], rows, [0.5, 2.2, 2.2, 0.6, 1.3], size=8)
    para(d, "All 14 first-level interactions and all eight second-level interactions carry an input/output that exists on the corresponding IDEF0 and appears in the corresponding cell of the N2 diagram, and every input/output of those IDEF0 diagrams that UC.1 uses appears in the sequence. The sequence is continuous: each interaction is triggered by an earlier one, from the precondition (factors loaded) through the Commute Impact Result (step 7) that ends the scenario. No input, control or output arrow is tunneled or left unconnected on the Metafunction, the first-level IDEF0 or the second-level IDEF0.")

    # ---------------------------------------------------------------- 2.2
    heading(d, "2.2 Physical Architecture", 2)
    heading(d, "2.2.1 Physical Architecture Model", 3)
    heading(d, "2.2.1.1 Physical Elements", 4)
    para(d, f"Each first-level function receives one subsystem, named for the capability it provides rather than for the function (a noun, no conjunction). {T('assets')} lists the eight first-level subsystems and what each is made of; at this level a subsystem is still an aggregate of software, data, documents and people, as the lab describes. {T('assets2')} lists the four modules of C.0.2. The hierarchy mirrors the functional hierarchy one to one: C.0 EcoCommute is decomposed by C.0.0 to C.0.7, as F.2 is decomposed by F.2.0 to F.2.7, and C.0.2 is decomposed by C.0.2.1 to C.0.2.4, as F.2.2 is decomposed by F.2.2.1 to F.2.2.4.")
    rows = [[v[0], v[1], f"{f} {M.L1NAME[f]}", v[3]] for f, v in P.ASSET1.items()]
    tab("assets", "First-level physical elements (subsystems).", ["Asset", "Name", "Performs", "Made of"], rows, [0.6, 1.5, 1.7, 3.0], size=8)
    rows = [[v[1], v[2], f"{f} {v[0]}", v[3]] for f, v in P.FUNC2.items()]
    tab("assets2", "Second-level physical elements (modules of C.0.2).", ["Asset", "Name", "Performs", "Made of"], rows, [0.7, 1.5, 1.7, 2.9], size=8)
    para(d, f"{F('meta')} is the Metafunction IDEF0 with its six mechanisms (Commuter, EcoCommute, Pilot Administrator, Open-Meteo, Emission Factor Publisher, Hosting Provider). {F('idef1')} is the first-level IDEF0 with the mechanisms added: each box has one mechanism, its subsystem (Innoslate draws the mechanism arrows from the parent asset at the bottom and labels each arrow with the performing subsystem). {F('idef2')} is the second-level IDEF0 of F.2.2 with the four module mechanisms. Together the three diagrams give IDEF0 to three levels, each with inputs, controls, outputs and mechanisms.")
    fig("meta", os.path.join(OLD, "trim_metafunction_idef0.png"), 6.2, "Metafunction IDEF0 from Innoslate: six top-level functions with their mechanisms at the bottom.")
    landscape()
    fig("idef1", os.path.join(DIA, "fig_idef0_first_mech.png"), 9.4, "First-level IDEF0 of F.2 with mechanisms (model 11.3): each function is performed by one subsystem C.0.k.")
    fig("idef2", os.path.join(DIA, "fig_idef0_second_mech.png"), 9.0, "Second-level IDEF0 of F.2.2 with mechanisms (model 11.3): each function is performed by one module C.0.2.m.")
    portrait()
    para(d, "**Walking-skeleton modules.** The four modules of the Chapter 2 code (C.1 to C.4) each serve more than one function, so they are not first-level assets. Their allocation to the new subsystems is below; the repository directories keep their names until the product-build increment of Chapter 8.5, when docs/deployment.md maps directories to subsystems.", after=3)
    tab("old", "Allocation of the walking-skeleton code modules to the subsystems.", ["Module", "Name", "Implements"], [list(x) for x in P.OLD_MODULES], [0.7, 1.7, 4.4], size=8.5)
    para(d, f"{T('tech')} records the technology each subsystem is built with and the existing element it reuses, taken from the repository and its architecture decision records (ADRs). It shows that seven of the eight subsystems already have an implementation; the Reporting Subsystem does not, because the pilot summary (UC.2) lies outside the implemented use cases.")
    tech = [["C.0.0 Operations", "Python 3.12 application served with Waitress; invite and account management command (src.manage); hosting by X.5", "ADR 0001, 0009"],
            ["C.0.1 Entry", "Flask web entry with validation, sign-up and log-in (C.1 web_app, auth)", "ADR 0002, 0009"],
            ["C.0.2 Reference Data", "Factor store (placeholder factors until reviewed ones are loaded); route adapter to OpenRouteService with labelled fallback; place and route cache in SQLite; TCAT timetable index", "ADR 0003, 0007, 0009"],
            ["C.0.3 Estimation", "CO2e calculation and mode comparison, with carpool share (C.2)", "ADR 0003, 0008"],
            ["C.0.4 Records", "SQLite database app.sqlite for users, trips and preferences; salted scrypt hashes; badge rules (C.2 achievements)", "ADR 0005, 0009"],
            ["C.0.5 Recommendation", "Rule-based recommendation (recommend_mode) and bus planner on the TCAT timetable (C.2)", "ADR 0004, 0006, 0007"],
            ["C.0.6 Presentation", "Flask result pages; explanation step (C.4), currently a template that restates calculated facts", "ADR 0002"],
            ["C.0.7 Reporting", "Not implemented yet; the campus tree total is computed in C.2", "ADR 0005"]]
    tab("tech", "Technologies and existing elements of the first-level subsystems.", ["Subsystem", "Technology and existing element", "Source"], tech, [1.4, 4.4, 1.0], size=8)
    heading(d, "2.2.1.2 Asset Hierarchy Diagrams", 4)
    para(d, f"{F('hier')} is the whole asset hierarchy to three levels below the Universe: C.0 and the seven external assets (level 1; X.6 and X.7 were added in model 11.0), the eight subsystems (level 2) and the four modules of C.0.2 (level 3). Because the full tree is too wide to read, it is partitioned: {F('hier0')} shows the context (Universe, C.0 and the external assets), {F('hier1')} shows C.0 with its eight subsystems and the function each performs, and {F('hier2')} shows C.0.2 with its four modules and the function each performs. Every asset has a number and a noun-oriented name, and every function-asset pair shares its last digits.")
    landscape()
    fig("hier", os.path.join(DIA, "fig_hier_overall.png"), 9.2, "Overall asset hierarchy (model 11.3), three levels below the Universe.")
    fig("hier0", os.path.join(DIA, "fig_hier_context.png"), 8.0, "Hierarchy partition 0: the Universe with C.0 and the external assets X.1 to X.7.")
    fig("hier1", os.path.join(DIA, "fig_hier_c0.png"), 9.2, "Hierarchy partition 1: C.0 EcoCommute decomposed into its eight first-level subsystems.")
    portrait()
    fig("hier2", os.path.join(DIA, "fig_hier_c02.png"), 6.4, "Hierarchy partition 2: C.0.2 Reference Data Subsystem decomposed into its four modules.")
    heading(d, "2.2.1.3 Non-Functional Considerations", 4)
    para(d, f"System-wide (non-functional) requirements cannot be allocated to one asset, so they are satisfied by the system asset C.0 and contributed to by the subsystems. In model 11.3 each of the 17 leaf requirements of 3.4 System-wide Requirements (11 from model 10.8, six added by models 10.9 and 11.0) is traced to C.0 with a satisfied-by relationship (Chapter 8 criterion). {T('nfr')} shows which subsystems contribute to each requirement: P marks the primary contributor, C a contributor. The matrix drives the selection of the component for flow-down in Section 3.2.2 and the weights in Section 2.4.")
    rows = []
    for k, (n, m) in P.NFR.items():
        rows.append([f"{k} {n}"] + [m.get(a, "") for a in P.A1])
    tab("nfr", "Contribution of the first-level subsystems to the system-wide requirements (P primary, C contributes).", ["Requirement"] + [a.replace("C.0.", "C.0.") for a in P.A1], rows, [2.5] + [0.55] * 8, size=7.5)
    para(d, "Observations: availability and response time involve every subsystem on the UC.1 path, so they are budgeted (apportionment); privacy and quality requirements have one or two primary owners; accessibility concerns only the two subsystems with a user interface; and the Reference Data Subsystem contributes to nine of the 17 requirements (cost, schedule, response time, availability, capacity, location privacy, factor resolution and, since model 11.0 allocated place suggestion to F.2.2, the Route Service data limit and the place-cache privacy rule), which supports choosing it for the flow-down.")

    heading(d, "2.2.1.4 Insights on the Mechanisms", 4)
    deg = {a: [0, 0, 0] for a in P.A1}
    for cid, nm_, a, b, ios, med in P.CONDUITS1:
        if a in deg and b in deg:
            deg[a][0] += 1
            deg[b][1] += 1
        else:
            deg[a if a in deg else b][2] += 1
    kind = {"C.0.0": "software, scripts, people", "C.0.1": "software (user interface)", "C.0.2": "software and reference data", "C.0.3": "software (calculation)",
            "C.0.4": "software and personal data", "C.0.5": "software (rules)", "C.0.6": "software (user interface, language step)", "C.0.7": "software, data and people"}
    rows = [[f"{a} {P.ASSET_SHORT[a]}", kind[a], deg[a][0], deg[a][1], deg[a][2]] for a in P.A1]
    tab("mech", "The mechanisms: what each is made of and how many conduits it has (internal conduits out and in, conduits to external assets).", ["Mechanism", "Mostly", "Out", "In", "External"], rows, [2.2, 2.4, 0.6, 0.6, 0.8], size=8.5)
    para(d, f"Four observations about the mechanisms follow from the allocation. (1) **The mechanisms are cohesive.** Each subsystem is named for one capability and holds one function, so a change to a rule (recommendation), a factor (reference data) or a view (presentation) stays inside one asset. (2) **Interfaces concentrate in two assets.** C.0.1 Entry sends to four subsystems and C.0.4 Records receives from three subsystems and has one external conduit, so these two define most of the internal interface work. (3) **Three mechanisms touch the outside world.** Reference Data has three external conduits (Open-Meteo twice, the Emission Factor Publisher once), Operations two (Hosting Provider, Pilot Administrator) and Reporting two (both with the Pilot Administrator); the Commuter reaches four subsystems, which is the IO.2 fan-out discussed in Section 2.3.1. (4) **Two mechanisms are partly people and process.** Operations (release, monitoring, retirement) and Reporting (small-group suppression rules set by the Pilot Administrator) are not only software, so their requirements are verified by analysis and demonstration rather than test alone ({T('sdor')}).")
    heading(d, "2.2.2 Physical Interface", 3)
    heading(d, "2.2.2.1 Asset Diagrams and I-Square Diagram", 4)
    para(d, f"The asset diagrams show the interfaces (conduits) between assets and the input/outputs that each conduit transfers. {F('ctx')} is the context asset diagram generated from the Metafunction IDEF0: C.0 interfaces with the five external assets over the eight conduits of model 10.8, each with its transfers relationships; the three conduits that model 11.0 added for X.6 and X.7 are shown with the grey assets X.6 and X.7 and transfer use-case-level input/outputs (Route Request, Route Options, Bus Schedule) that have no top-level function yet. {F('asset1')} is the first-level asset diagram generated from the first-level IDEF0. It has 24 conduits: 11 between a subsystem and an external asset and 13 between subsystems. {T('conduits')} lists each conduit, its endpoints, the medium and what it transfers. The 22 first-level input/outputs are all transferred by at least one conduit, and each conduit transfers only input/outputs that appear on the IDEF0 between the same two functions.")
    ctxrows = [["Trip details", "X.1 > C.0", "IO.1, IO.2", "Yes"], ["Result and advice", "C.0 > X.1", "IO.3", "Yes"], ["Weather query", "C.0 > X.3", "IO.4", "Yes"],
               ["Forecast", "X.3 > C.0", "IO.5", "Yes"], ["Reviewed factors", "X.4 > C.0", "IO.6", "Yes"], ["Summary request", "X.2 > C.0", "IO.7, IO.9", "Yes"],
               ["Approved aggregates", "C.0 > X.2", "IO.8", "Yes"], ["Hosting service", "C.0 > X.5 and X.5 > C.0", "IO.10, IO.11", "Yes"],
               ["Route request, Route response, Transit schedule", "C.0 and X.6, X.7", "Route Request, Route Options, Bus Schedule", "Added by model 11.0; no top-level function"]]
    para(d, f"{T('ctxio')} lists the transfers relationship of each context conduit and compares it with the Metafunction IDEF0: all 11 input/outputs of the Metafunction are transferred, each between the two assets whose functions exchange it.")
    tab("ctxio", "Context conduits, the input/outputs they transfer and agreement with the Metafunction IDEF0.", ["Conduit", "Direction", "Transfers", "Matches Metafunction"], ctxrows, [2.0, 1.6, 1.8, 1.4], size=8.5)
    fig("ctx", os.path.join(DIA, "fig_asset_context.png"), 5.8, "Context asset diagram of C.0 EcoCommute with its seven external assets (model 11.3; conduit names as in models 10.8 and 11.0).")
    landscape()
    fig("asset1", os.path.join(DIA, "fig_asset_first.png"), 6.4, "First-level asset diagram: eight subsystems, five external assets and 24 conduits; arrows show the direction of the conduit, and each conduit with its transferred input/outputs is listed in the conduit table.")
    portrait()
    rows = []
    for cid, name, a, b, ios, med in P.CONDUITS1 + P.CONDUITS2:
        rows.append([cid, name, f"{a} {A.get(a, a)} ↔ {b} {A.get(b, b)}", med, ", ".join(i.replace("IO.", "") for i in ios)])
    tab("conduits", "Conduits (interfaces) of the first-level asset diagram (K.1 to K.24) and of C.0.2 (K.2.1, K.2.2). Last column: IO numbers transferred.", ["Id", "Conduit", "Connects", "Medium", "IO"], rows, [0.5, 1.35, 2.5, 1.9, 0.6], size=7.5)
    para(d, f"{F('i2a')} is the I2 (interface-square) diagram of the first level. The subsystems sit on the diagonal; the cell in a row and column holds the conduit that carries information from the row's subsystem to the column's subsystem and the input/outputs it transfers; the top row holds the interfaces from external assets and the right-hand column those to external assets; a conduit that carries flows both ways (K.1, K.11) appears once, under the asset where its flow originates. The diagram makes three things visible. First, the interfaces are sparse: 13 of the 56 possible subsystem pairs are used, so coupling is low. Second, C.0.1 Entry is a hub (K.12 to K.15 carry the validated entry to four subsystems) and C.0.4 Records receives from three subsystems, so these two are the places where interface changes would ripple. Third, no subsystem pair interacts in both directions, so there are no cycles. {F('i2b')} is the I2 diagram of the four modules of C.0.2: only two internal conduits exist (K.2.1 and K.2.2). The conduits that cross the boundary of C.0.2 (K.5, K.6, K.7, K.12, K.16, K.17) connect to C.0.2 as a whole in the model; their allocation to the module that owns each one is given by the sequence diagram (Figure 5) and by the interface requirements 5.3.1 to 5.3.8.")
    landscape()
    fig("i2a", os.path.join(DIA, "fig_i2_first.png"), 6.1, "I2 diagram of the first-level assets (model 11.3).")
    portrait()
    fig("i2b", os.path.join(DIA, "fig_i2_second.png"), 4.6, "I2 diagram of the second-level assets of C.0.2 (model 11.3).")

    # ---------------------------------------------------------------- 2.3
    heading(d, "2.3 Architecture Evaluation", 2)
    heading(d, "2.3.1 Analysis against Functional Architecture", 3)
    para(d, f"The physical architecture is checked against the functional architecture in six ways ({T('evalchk')}). The checks were run by script on the model data so they can be repeated.")
    rows = [
        ["One performer per function", "Each of F.2.0 to F.2.7 and F.2.2.1 to F.2.2.4 has exactly one performed-by asset; each asset performs exactly one function.", "Met (12 of 12 functions)"],
        ["Hierarchy mirrors function", "C.0 is decomposed by 8 subsystems as F.2 is by 8 functions; C.0.2 by 4 modules as F.2.2 by 4 functions; no other asset is decomposed.", "Met"],
        ["Interfaces carry the flows", "Every first-level flow, from a source function (or external asset) to each destination, has a conduit between the performing assets that transfers it; no conduit transfers an input/output absent from the IDEF0.", "Met (22 of 22 input/outputs; 24 conduits)"],
        ["Second level closes the first", "All six flows of F.2.2 enter or leave a second-level function of F.2.2; IO.23 and IO.24 stay inside.", "Met (6 of 6)"],
        ["Sequence runs on assets", "The UC.1 sequence (Figures of Section 2.1.3.2) is continuous over the lifelines C.0.1 to C.0.6 and the external assets, with no interaction lacking a conduit.", "Met (14 of 14; 8 of 8)"],
        ["No tunnels", "No tunnel on the Metafunction, the first-level or the second-level IDEF0; no unconnected perimeter arrow.", "Met"],
    ]
    tab("evalchk", "Analysis of the physical architecture against the functional architecture.", ["Check", "What was compared", "Result"], rows, [1.6, 3.9, 1.3], size=8.5)
    para(d, f"The analysis also exposed three observations that do not break the criteria but should shape detailed design. (1) IO.2 Commuter Consent and Settings enters three functions from the environment (F.2.1, F.2.4, F.2.5), which creates three Commuter-facing conduits (K.1, K.3, K.4). Physically the settings page belongs to the Entry Subsystem, which would pass the values on; the functional architecture was baselined in Chapter 7, so the model keeps three conduits and flags the refinement for detailed design. (2) The two interface hubs identified in Section 2.2.1.4 (C.0.1 Entry and C.0.4 Records) should have their interface definitions frozen first. (3) The Presentation Subsystem receives from three subsystems (C.0.3, C.0.4 and C.0.5), which is expected for an assembly function but makes its timing budget the longest dependent chain (Section 3.2.2).")

    # ---------------------------------------------------------------- 2.4
    heading(d, "2.4 Alternative Physical Architectures", 2)
    heading(d, "2.4.1 Evaluation of Physical Alternatives", 3)
    para(d, f"Three first-level physical architectures were considered. Alternative A is the one-to-one functional architecture of this section. Alternative B keeps the four modules of the Chapter 2 walking skeleton (C.1 to C.4) as the first-level assets. Alternative C is a conventional three-tier layering (web tier, service tier, data tier) with separate operations and reporting assets. {T('crit')} lists the criteria with their weights and the reason for each; {T('alts')} scores the alternatives from 1 (poor) to 5 (good).")
    tab("crit", "Evaluation criteria and weights (sum 100).", ["Criterion", "Weight", "Why it matters"], [[n, w, why] for n, w, why in P.CRITERIA], [1.7, 0.6, 4.5], size=8.5)
    rows = []
    for ci, (n, w, _) in enumerate(P.CRITERIA):
        rows.append([n, w] + [v[2][ci] for v in P.ALTS.values()])
    tot = {k: sum(w * s for (_, w, _), s in zip(P.CRITERIA, v[2])) / 100 for k, v in P.ALTS.items()}
    rows.append(["**Weighted score**", "100"] + [f"**{tot[k]:.2f}**" for k in P.ALTS])
    tab("alts", "Scores of the alternatives. A: functional subsystems; B: walking-skeleton modules; C: three-tier layers.", ["Criterion", "Weight", "A", "B", "C"], rows, [2.8, 0.7, 0.8, 0.8, 0.8], size=8.5)
    fig("altc", os.path.join(DIA, "fig_alt_scores.png"), 5.0, "Weighted scores of the three physical alternatives.")
    for k, (n, desc, _) in P.ALTS.items():
        para(d, f"**Alternative {k}, {n}.** {desc} {P.ALT_NOTES[k]}")
    para(d, f"Alternative A scores {tot['A']:.2f}, against {tot['B']:.2f} for B and {tot['C']:.2f} for C, and is the only one that meets the Chapter 8 one-to-one rule. It is selected. Its weaknesses are the interface count and the gap to the existing code; the first is a cost the lab accepts for traceability, the second is closed by {T('old')}. The scores are team judgements. A leads by more than one point, and shifting 10 points of weight between any two criteria changes a weighted score by at most 0.4, so the ranking holds.")

    # ============================================================ 3 Requirements
    heading(d, "3 System Requirements Management", 1)
    heading(d, "3.1 Requirements Traceability", 2)
    g = model_counts()
    para(d, f"Chapter 8 also completes the system-level specification. Document 3 of the model was generated from the Metafunction and first-level IDEF0 (sections 3.1 to 3.3, with the input, output, interface and functional requirements) and edited; the non-functional requirements of section 3.4 were added by hand and traced to the system asset. {T('syssp')} gives the leaf requirement count of each section after the update. The 17 leaf requirements of 3.4 are satisfied by C.0, and every functional requirement 3.3.1.k is satisfied by the function F.2.k that performs it and, through the allocation, by its subsystem.")
    tab("syssp", "System requirements document (3) after the update: leaf requirements per section.", ["Section", "Content", "Leaf requirements"],
        [["3.1.1", "Input requirements (accept ... from ...)", g["3.1.1"]], ["3.1.2", "Output requirements (provide ... to ...)", g["3.1.2"]], ["3.2", "External interface requirements (utilize ... to interface with ...)", g["3.2"]],
         ["3.3", "Functional requirements (one per function)", g["3.3"]], ["3.4", "System-wide requirements: cost and schedule, performance, availability and capacity, accessibility, privacy and security, estimation quality", g["3.4"]]], [0.8, 4.8, 1.2], size=8.5)
    para(d, f"{F('spider')} is the spider diagram of the Reference Data Subsystem, C.0.2, from model 11.3. At the centre is the asset; around it are the functions it performs (F.2.2 and its four sub-functions), the modules that decompose it, the conduits that cross or lie inside it, the system requirements the component requirements are traced from, and the five groups of component requirements it satisfies. The same relationships exist for every first-level subsystem: each leaf function has a performed-by asset, a satisfied-by design output requirement (documents 4 and 5 of the model) and a traced-from system requirement 3.3.1.x.")
    fig("spider", os.path.join(DIA, "fig_spider.png"), 6.7, "Spider diagram of C.0.2 Reference Data Subsystem: functions, modules, conduits, system requirements and component requirements.")
    rows = []
    for r in Q.SDOR:
        rows.append([P.FUNC_OF[r["asset"]], f"{r['asset']} {A[r['asset']]}", r["num"], ", ".join(r["parents"]), ", ".join(r["stk"])])
    rows.append(["F.2.2", "C.0.2 Reference Data Subsystem", "5.4.1 to 5.4.4", "3.3.1.2", "2.4.1, 2.1.4, 2.1.3, 2.5.1"])
    tab("trace", "Function, asset, design output requirement, system requirement and stakeholder requirements for every first-level function.", ["Function", "Asset", "Design output requirement", "System requirement", "Stakeholder requirements"], rows, [0.7, 1.9, 1.2, 1.1, 1.9], size=8)
    new11 = [("3.3.1.9", "compare travel modes", "F.2.3, F.2.5", "C.0.3 Estimation, C.0.5 Recommendation"),
             ("3.3.1.10", "confirm completed trips", "F.2.4", "C.0.4 Records"), ("3.3.1.11", "evaluate achievements", "F.2.4", "C.0.4 Records"),
             ("3.3.1.12", "track campus progress", "F.2.4, F.2.6", "C.0.4 Records, C.0.6 Presentation"),
             ("3.3.1.13", "plan direct bus rides", "F.2.5", "C.0.5 Recommendation"),
             ("3.3.1.14", "share a car trip's emissions among its occupants", "F.2.3", "C.0.3 Estimation"),
             ("3.3.1.15", "manage accounts and invite codes", "F.2.4", "C.0.4 Records"), ("3.3.1.16", "keep trips per account", "F.2.4", "C.0.4 Records"),
             ("3.3.1.17", "suggest places and remember answers", "F.2.2", "C.0.2 Reference Data")]
    para(d, f"Models 10.9 and 11.0 added the trip planner (UC.3) and accounts (UC.4) and nine functional requirements, 3.3.1.9 to 3.3.1.17. They were allocated to the existing first-level functions without adding a function, so each lands on an existing subsystem ({T('new11')}): the form architecture absorbs the new features without a new asset. Two consequences follow. The Records Subsystem takes five of the nine, which confirms it as an interface and load hub (Section 2.3.1). And 3.3.1.17 (place suggestion and the persistent place cache) enlarges F.2.2 beyond the four second-level functions of this section; a fifth function, Suggest Places, with a module C.0.2.5, is the planned next step, and the two system-wide requirements that touch it are already flowed down (5.5.8 and 5.5.9). The model keeps the walking-skeleton modules C.1 to C.4 as performers of the UC.3 and UC.4 actions, because the code tests read them; they are a code view of the subsystems ({T('old')}).")
    tab("new11", "Functional requirements added in models 10.9 and 11.0, the first-level function they are allocated to, and the subsystem that performs it.", ["Requirement", "Name", "Function", "Subsystem"], [list(x) for x in new11], [0.8, 3.0, 1.1, 1.9], size=8.5)
    para(d, "The model also keeps the earlier traces: the 17 system-wide requirements are satisfied by C.0; the functional requirements 3.3.1.k remain satisfied by the functions F.2.k; the external interface requirements 3.2.1 to 3.2.8 remain satisfied by C.0 and the external assets and are now also satisfied by the conduits that realise them.")

    heading(d, "3.2 System Design Output Requirements", 2)
    heading(d, "3.2.1 Methodology for Deriving System Design Output Requirements", 3)
    para(d, "A system design output requirement (SDOR) states what a form entity must do, in the form \"The [named subsystem] shall ...\", so that its designer can design and test to it. The team derived them in five steps.")
    for t in ["**Select the leaf functions.** A leaf function is a function that is not decomposed: F.2.0, F.2.1 and F.2.3 to F.2.7 at the first level and F.2.2.1 to F.2.2.4 at the second level (11 in all).",
              "**Find the performer.** Use the one-to-one allocation of Section 2.2.1.1; the subject of the requirement is that asset.",
              "**State the requirement.** One \"shall\" per requirement, with the function as its predicate. For leaf first-level functions, the statement restates the system functional requirement 3.3.1.k for the subsystem and adds the specific obligation that makes it testable (validate, restrict, suppress, restate only calculated facts).",
              "**Map, justify and measure.** Each requirement names its higher-level requirement (the system requirement 3.3.1.k, or for second-level functions 3.3.1.2), its stakeholder requirements, its rationale, a measure of performance (MOP) with a target or threshold and verification criteria with a method (Test, Inspection, Analysis, Demonstration). Targets are those of the stakeholder requirements.",
              "**Complete the component specification.** For the component chosen in Section 2.1.1.3, add the input, output, interface and system-wide requirements of Chapter 9. Input and output requirements come from the first-level flows of F.2.2 (internal second-level flows IO.23 and IO.24 stay out because they do not cross the component boundary); interface requirements come from the conduits that cross the boundary; system-wide requirements come from 3.4 by equivalence, apportionment or synthesis."]:
        bullet(d, t)
    para(d, "The three flow-down methods are used as follows. **Equivalence** applies the same requirement to the component when it cannot be shared out (capacity, privacy limits). **Apportionment** divides a quantity that adds up across the system (cost, time, unavailability) so that the shares total 100% of the system value including a reserve. **Synthesis** derives a component value from a system value through an engineering relationship (here, factor resolution from a rounding tolerance and a longest trip). The method is stated for every system-wide requirement with the reason it was chosen.")

    heading(d, "3.2.2 Detailed System Design Output Requirements", 3)
    heading(d, "3.2.2.1 Subsystem Design Output Requirements", 4)
    para(d, "The seven leaf first-level functions have one design output requirement each, in document 4 of the model. They are presented in the summary table of Section 3.2.3 together with the second-level requirements. All use the form \"The [named] Subsystem shall ...\", map to a system functional requirement, and carry rationale, MOP and verification criteria.")
    heading(d, "3.2.2.2 Component Specification for the Reference Data Subsystem", 4)
    nI, nO, nF, nS = len(Q.INPUT), len(Q.OUTPUT), len(Q.INTERFACE), len(Q.SYSWIDE)
    para(d, f"The component specification (document 5 of the model) is kept apart from the system requirements, as the lab requires. It contains {len(Q.INPUT + Q.OUTPUT + Q.INTERFACE + Q.FUNCTIONAL + Q.SYSWIDE)} requirements: {nw(nI)} input, {nw(nO)} output, {nw(nF)} interface, {nw(len(Q.FUNCTIONAL))} functional (one for each of F.2.2.1 to F.2.2.4, so every function of the second-level IDEF0 has exactly one requirement) and {nw(nS)} system-wide. {T('compio')} gives the input, output and interface requirements; the functional requirements are in {T('sdor')}; and the system-wide requirements are in {T('sysw')}. Every input, control and output that enters or leaves the second-level IDEF0 has a requirement: IO.5, IO.6 and IO.12 as inputs (5.1.1 to 5.1.3) and IO.4, IO.14 and IO.15 as outputs (5.2.1 to 5.2.3). An interface requirement exists for each external asset the component touches: Open-Meteo through the Weather query and Forecast conduits (5.3.1, 5.3.2), the Emission Factor Publisher through Reviewed factors (5.3.3) and, since model 11.0 allocated place suggestion to F.2.2, the Route Service through Route request and Route response (5.3.7, 5.3.8); and for each neighbouring subsystem (Entry, Estimation, Recommendation; 5.3.4 to 5.3.6).")
    rows = []
    for r in Q.INPUT + Q.OUTPUT + Q.INTERFACE:
        rows.append([r["num"], r["stmt"], ", ".join(r["parents"]), r["rat"], r["mop"], f"{r['ver']} ({r['method']})"])
    landscape()
    tab("compio", "Component specification, input, output and interface requirements for C.0.2 (document 5, sections 5.1 to 5.3).", ["ID", "Requirement", "Parent", "Rationale", "MOP", "Verification criteria (method)"], rows, [0.45, 2.4, 0.75, 2.3, 1.9, 1.9], size=7.5)
    heading(d, "3.2.2.3 System-Wide Requirements Flow-Down", 4)
    para(d, f"{T('sysw')} lists the {nw(len(Q.SYSWIDE))} system-wide requirements flowed down to C.0.2 and the method for each, with the reason. {cap(nw(len(Q.OMITTED)))} requirements of 3.4 were left out because the component does not influence them ({T('omit')}). The three apportionment budgets follow: cost ({T('cost')}), response time ({T('time')}) and unavailability ({T('avail')}). Each budget totals the system value, so the sum of the subsystem requirements guarantees the system requirement when the subsystems are integrated.")
    rows = []
    for r in Q.SYSWIDE:
        rows.append([r["num"], r["stmt"], r["parents"][0], f"**{r['flow']}**. {r['rat']}", r["mop"], f"{r['ver']} ({r['method']})"])
    tab("sysw", "System-wide requirements of the Reference Data Subsystem with flow-down method and rationale (document 5, section 5.5).", ["ID", "Requirement", "System req.", "Method and rationale", "MOP", "Verification criteria (method)"], rows, [0.45, 2.0, 0.6, 3.0, 1.5, 2.1], size=7.5)
    portrait()
    para(d, f"{T('miles')} gives the schedule and where the project stands on October 30, 2026. The web application is already implemented (the use cases UC.1, UC.3 and UC.4 run, with an automated test suite), so the project is at the end of subsystem implementation and at the start of verification and integration. Two dates are fixed: system verification ends on December 2, 2026 and the sponsor's results are due on December 18, 2026. Working back from them, the integration date of requirement 5.5.2 is November 13, 2026 and the pilot starts on November 16, which allows four weeks of use. The earlier assumption of eight weeks does not fit, so the weekly-active-use measure of stakeholder requirement 2.1.6 is set to week four in model 11.3 (it read week eight); the sponsor should confirm this change, and the 40% target was not changed. Status is as reported by the team.")
    tab("miles", "Schedule milestones, with status on October 30, 2026.", ["Date", "Milestone", "Owner or note", "Status"], [list(x) for x in Q.MILESTONES], [0.85, 3.7, 1.5, 0.75], size=8.5)
    tab("omit", "System-wide requirements not flowed down to C.0.2, with the reason.", ["System requirement", "Reason it does not apply"], [[f"{a} {b}", c] for a, b, c in Q.OMITTED], [2.4, 4.4], size=8.5)
    tab("cost", "Apportionment of the $750,000 cost requirement (3.4.1.1).", ["Subsystem", "Share", "Budget"],
        [[f"{k} {A[k]}" if k in A else k, f"{v}%", f"${v * 7500:,.0f}"] for k, v in Q.COST_BUDGET] + [["**Total**", "**100%**", "**$750,000**"]], [3.2, 1.0, 1.4], size=8.5)
    tab("time", "Apportionment of the 3-second result time (3.4.2.1) along the UC.1 path, summed serially as a conservative assumption.", ["Subsystem", "Time (s)"],
        [[f"{k} {A[k]}" if k in A else k, f"{v:.1f}"] for k, v in Q.TIME_BUDGET] + [["**Total**", "**3.0**"]], [3.2, 1.0], size=8.5)
    tab("avail", "Apportionment of the 0.5% monthly unavailability allowed by 3.4.3.1 across the subsystems on the UC.1 path.", ["Subsystem", "Unavailability allowed", "Availability required"],
        [[f"{k} {A[k]}" if k in A else k, f"{v:.2f}%", f"{100 - v:.2f}%" if k in A else ""] for k, v in Q.AVAIL_BUDGET] + [["**Total**", "**0.50%**", "**99.50%**"]], [3.2, 1.4, 1.4], size=8.5)

    heading(d, "3.2.3 Summary Table of System Design Output Requirements", 3)
    para(d, f"{T('sdor')} summarises the design output requirements of all 11 leaf functions that are allocated to form entities: the seven first-level subsystems and the four functions of the Reference Data Subsystem. Each row has the requirement, the higher-level requirement it maps to, the rationale, the MOP and the verification criteria with the method.")
    rows = []
    for r in Q.SDOR:
        rows.append([r["num"], f"{r['asset']} {A[r['asset']]} / {P.FUNC_OF[r['asset']]}", r["stmt"], ", ".join(r["parents"]), r["rat"], r["mop"], f"{r['ver']} ({r['method']})"])
    for r in Q.FUNCTIONAL:
        rows.append([r["num"], f"{r['asset']} {A[r['asset']]} / {r['func']}", r["stmt"], ", ".join(r["parents"]), r["rat"], r["mop"], f"{r['ver']} ({r['method']})"])
    landscape()
    tab("sdor", "Summary of system design output requirements for the leaf functions allocated to form entities (documents 4 and 5).", ["ID", "Asset / function", "Requirement", "Parent", "Rationale", "MOP", "Verification criteria (method)"], rows, [0.4, 1.0, 2.2, 0.55, 1.9, 1.8, 1.75], size=7)
    portrait()

    # ============================================================ 4 Summary
    heading(d, "4 Summary", 1)
    para(d, "The first-level physical architecture of EcoCommute has eight subsystems, C.0.0 Operations, C.0.1 Entry, C.0.2 Reference Data, C.0.3 Estimation, C.0.4 Records, C.0.5 Recommendation, C.0.6 Presentation and C.0.7 Reporting, one for each first-level function. Their 24 conduits, 11 to external assets and 13 between subsystems, transfer all 22 first-level input/outputs, and the I2 diagram shows the coupling is low. The most complex function, F.2.2 Manage Reference Data, was decomposed into four functions performed by four modules, with two new internal flows that close the baseline scenario. IDEF0 diagrams with mechanisms now exist for three levels, with no tunneled or unconnected input, control or output arrows.")
    para(d, f"The analysis against the functional architecture found no violation; it flagged IO.2 reaching three subsystems directly, and the hub role of Entry and Records, for detailed design. Of three alternatives, the functional subsystems scored {tot['A']:.2f} against {tot['B']:.2f} and {tot['C']:.2f}. For requirements, 11 design output requirements cover all leaf functions, each with parent, rationale, MOP and verification; the component specification for C.0.2 has {len(Q.INPUT + Q.OUTPUT + Q.INTERFACE + Q.FUNCTIONAL + Q.SYSWIDE)} requirements, {nw(len(Q.SYSWIDE))} of them flowed down from the system-wide requirements by equivalence ({sum(r["flow"] == "Equivalence" for r in Q.SYSWIDE)}), apportionment ({sum(r["flow"] == "Apportionment" for r in Q.SYSWIDE)}) and synthesis ({sum(r["flow"] == "Synthesis" for r in Q.SYSWIDE)}) with budgets that sum to the system values.")
    para(d, "Open items: the budgets, the November 13, 2026 integration date, the four-week pilot window (the measure of requirement 2.1.6 was moved from week eight to week four in model 11.3) and the 3-second and group-size-5 values remain educated guesses or proposals pending sponsor confirmation; the third level of F.2.2.1 is planned for the final assignment; place suggestion, which model 11.0 allocated to F.2.2, needs a fifth second-level function in the next iteration; and the repository code layout needs the allocation of the walking-skeleton table applied in the product build.")

    # ============================================================ Appendices
    heading(d, "Appendix A. Model Assessment Check", 1)
    para(d, f"{T('chk1')} checks the work against the First-Level IDEF0 Assessment Criteria of Chapter 8 and {T('chk2')} against the Second-Level Form Architecture and Component Specification Criteria of Chapter 9.")
    tab("chk1", "First-level IDEF0 assessment criteria (Chapter 8).", ["Criterion", "Status", "Evidence"], [
        ["Each first-level function is performed by exactly one appropriately named asset", "Met", f"{T('assets')}; {F('idef1')}"],
        ["Top-level system is decomposed by the subsystems on the first-level IDEF0, one to one", "Met", f"{F('hier1')}"],
        ["No tunnels on the Metafunction or first-level IDEF0", "Met", "Sections 2.1.2.1 and 2.1.3.3"],
        ["Universe asset diagram shows conduits that transfer input/outputs consistent with the Metafunction", "Met", f"{F('ctx')}"],
        ["System asset diagram shows conduits that transfer input/outputs consistent with the first-level IDEF0", "Met", f"{F('asset1')}; {T('conduits')}"],
        ["System-wide requirements added to the system requirements document", "Met", "Section 3.4 of document 3 (17 leaf requirements, reviewed here)"],
        ["Leaf-level system-wide requirements satisfied by the system asset", "Met", "All 17 leaf requirements of 3.4 satisfied by C.0 in model 11.3"],
    ], [3.7, 0.7, 2.4], size=8.5)
    tab("chk2", "Second-level form architecture and component specification criteria (Chapter 9).", ["Criterion", "Status", "Evidence"], [
        ["Each second-level function is performed by exactly one asset", "Met", f"{T('assets2')}; {F('idef2')}"],
        ["No tunnels on the Metafunction, first-level or second-level IDEF0", "Met", "Section 2.1.3.3"],
        ["Component input, output and functional requirements read \"The [named] subsystem shall ...\"", "Met", f"{T('compio')}; {T('sdor')}"],
        ["Every input, control and output of the second-level IDEF0 has an input or output requirement", "Met", "5.1.1 to 5.1.3 and 5.2.1 to 5.2.3 for IO.12, IO.5, IO.6, IO.4, IO.14, IO.15"],
        ["Every second-level function has exactly one functional requirement", "Met", "5.4.1 to 5.4.4"],
        ["An external interface requirement exists for each external system the component interacts with", "Met", "5.3.1 and 5.3.2 (Open-Meteo), 5.3.3 (Emission Factor Publisher)"],
        ["A sample system-wide component requirement exists for every pertinent system-wide requirement", "Met", f"{T('sysw')} ({len(Q.SYSWIDE)}); omissions justified in {T('omit')}"],
        ["Flow-down has a rationale and a stated method", "Met", f"{T('sysw')}"],
        ["System-wide requirements are satisfied by the pertinent subsystem asset", "Met", "5.5.1 to 5.5.9 satisfied by C.0.2 in model 11.3"],
    ], [3.7, 0.7, 2.4], size=8.5)
    heading(d, "Appendix B. Model Baseline and Figure Sources", 1)
    para(d, "**Model baseline.** The architecture of this section is model 11.3 of the Innoslate project. Its lineage is: 10.8 (function architecture of Chapters 6 and 7); 10.9 (web flow: trip planner UC.3, Route Service X.6); 11.0 (accounts, bus timetable, vehicles, carpool and place suggestions: UC.4, X.7); 11.2 (this section: first-level subsystems C.0.0 to C.0.7, modules C.0.2.1 to C.0.2.4, second-level functions F.2.2.1 to F.2.2.4, input/outputs IO.23 and IO.24, 24 first-level and two second-level conduits, documents 4 and 5 with their requirements, and the trace of every leaf system-wide requirement to C.0); 11.3 (adds the two Route Service interface requirements 5.3.7 and 5.3.8). Model 11.2 was imported into Innoslate and Innoslate Intelligence reported a pass rate of 74% with no errors and warnings only; 11.3 adds two requirements to it. The walking-skeleton modules C.1 to C.4 remain in the model as performers of the UC.3 and UC.4 actions but are detached from C.0. The export is docs/model/EcoCommute_11.3_C8-C9_physical_architecture.xml and the scripts that built the report and the model are in docs/ch8-ch9/build/. Two requirement texts were changed in the model: 3.4.1.2 and 2.3.4 now read December 18, 2026, and 2.1.6 measures weekly active use after four weeks (it read eight); both changes need sponsor confirmation.")
    meta_src = "Innoslate screenshot, model 10.8 (Chapters 6 and 7)"
    srcs = {"n2a": meta_src, "action": meta_src, "seq1": "Drawn from the model data (Innoslate cannot show internal interactions)", "seq2": "Drawn from the model data (Innoslate cannot show internal interactions)",
            "altc": "Chart of " + T("alts")}
    rowsb = []
    for k in REG["fig"]:
        if SHOTS.get(k) and os.path.exists(os.path.join(SHOTDIR, SHOTS[k])):
            src = "Innoslate screenshot, model 11.2"
        elif k == "meta":
            src = meta_src
        elif k in srcs:
            src = srcs[k]
        else:
            src = "Drawn from the model data in the style of Innoslate"
        rowsb.append([F(k), src])
    tab("shots", "Source of every figure.", ["Figure", "Source"], rowsb, [1.0, 5.8], size=8.5)
    header_footer(d, "EcoCommute Team 6 | SYSEN 5151 | Architecture Definition: Form (Chapters 8 and 9)")
    # ask Word to refresh the TOC on open
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    st = d.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    st.append(uf)
    return d


if __name__ == "__main__":
    probs = P.check() + Q.check()
    if probs:
        sys.exit(f"data checks failed: {probs}")
    build()
    NUM["fig"] = {k: i + 1 for i, k in enumerate(REG["fig"])}
    NUM["tab"] = {k: i + 1 for i, k in enumerate(REG["tab"])}
    d = build()
    d.save(OUT)
    print("saved", OUT, len(REG["fig"]), "figures", len(REG["tab"]), "tables")
