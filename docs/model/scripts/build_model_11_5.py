"""Build Innoslate model 11.5 from 11.4: the evaluation criteria, the physical architecture alternatives and the
decision of Chapter 11, and the risks of Chapter 12.

    python docs/model/scripts/build_model_11_5.py

Reads  docs/model/EcoCommute_11.4_C10_simulation.xml
Writes docs/model/EcoCommute_11.5_C11-C12_analysis_risk.xml

Adds (nothing of 11.4 is removed):
  - Statements EC.1 to EC.6: the evaluation criteria with metric, unit, value function, importance and swing weight, each traced
    to the requirement(s) it comes from;
  - Statement DEC.1: the decision (plan-path dispatch) with the alternatives, the scores and the selection;
  - Assets AL.A to AL.E: the physical architecture alternatives, each related to C.0.2 and C.0.6 and to the alternatives it builds
    on; the selected one satisfies requirement 3.4.2.1;
  - Risks TR.16 to TR.22 and new Probability and Consequence on the existing risks, from docs/ch11/sim/model.py (rating r of
    1 to 5 is written as (r - 0.5) / 5, the middle of the band of the Innoslate risk matrix); each risk is related to the
    requirements, functions, input/outputs and assets it comes from.
Probability and Consequence are the team's ratings (docs/risks.md). Relation names are the schema's own ('relates', 'traced to',
'satisfies'); the schema does not restrict them by class. Not yet imported in this form.
"""
import copy
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MODEL_DIR))
SRC = os.path.join(MODEL_DIR, "EcoCommute_11.4_C10_simulation.xml")
OUT = os.path.join(MODEL_DIR, "EcoCommute_11.5_C11-C12_analysis_risk.xml")
sys.path.insert(0, os.path.join(ROOT, "docs", "ch11", "sim"))
import model as AN  # noqa: E402

_spec = importlib.util.spec_from_file_location("build_model_10_9", os.path.join(HERE, "build_model_10_9.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Model(base.Model):
    """Model whose _write_rel also accepts a relation name the schema defines but no pair of classes uses yet."""

    def __init__(self, path):
        super().__init__(path)
        self.by_name = {c.findtext("name"): c.get("id") for c in self.root.find("schema") if c.tag == "schemaRelation"}

    def _write_rel(self, a, name, b):
        key = (self.cls(a), name, self.cls(b))
        if key not in self.rel_ids:
            self.rel_ids[key] = self.by_name[name]
        super()._write_rel(a, name, b)


def band(rating):
    return round((rating - 0.5) / 5.0, 2)


def p(text):
    return f"<p>{esc(text)}</p>"


def build():
    m = Model(SRC)
    m.rng.seed(1150)
    a = json.load(open(os.path.join(ROOT, "docs", "ch11", "data", "analysis.json"), encoding="utf-8"))
    t_stmt = m.find("1.1.8", "Statement")
    t_asset = m.find("C.0.2", "Asset")
    t_risk = m.find("TR.3", "Risk")
    req = lambda n: m.find(n, "Requirement")  # noqa: E731
    selected = a["selected"]

    # ---- criteria -----------------------------------------------------------------------------------------
    crit = {}
    for w in a["weights"]:
        text = (f"Metric: {w['unit']}. Best (value 100): {w['best']:g}. Worst (value 0): {w['worst']:g}. Value function: linear between the two. "
                f"Importance {w['importance']} ({w['why']}). Variation {w['variation']} (range of value scores {w['range']:.0f}). "
                f"Swing weight {w['swing']:g}, normalised weight {w['weight']:.3f}. Traced to requirements {w['req']} and stakeholder need {w['need']}.")
        e = m.add("crit:" + w["id"], t_stmt, w["id"], f"Evaluation criterion: {w['name']}", p(text))
        crit[w["id"]] = e
        for rn in [x.strip() for x in w["req"].split(",")]:
            try:
                m.link(e, "traced to", req(rn))
            except SystemExit:
                print("requirement not in the model:", rn)

    # ---- alternatives -------------------------------------------------------------------------------------
    alts = {}
    notes = {
        "A": "Sequential dispatch (as built). The plan asks the route service and then the weather service in the request thread; connections are opened on demand.",
        "B": "Concurrent dispatch. The weather call starts as soon as the start place is known and runs beside the route calls; the plan waits for the slower one.",
        "C": "Concurrent dispatch with keep-alive. As B, plus a background loop that asks each service a light question every 20 s to keep one connection open.",
        "D": "Concurrent dispatch with a name cache. As B, plus an in-process cache of the two hosts' addresses (stale-while-revalidate, filled at start-up) so a new connection does not wait for a name lookup.",
        "E": "Queued asynchronous handling. The plan request is queued and answered at once with a status page; a worker does the calls and the page polls for the result. Not built.",
    }
    for key, name in AN.ALTS.items():
        sc = a["totals"][key]["score"]
        text = (f"{notes[key]} Effectiveness score {sc:.1f} of 100; life cycle cost over {a['assumptions']['life_years']} years "
                f"${a['lcc'][key]['total']:,.0f}. {'SELECTED.' if key == selected else 'Not selected.'}")
        e = m.add("alt:" + key, t_asset, f"AL.{key}", f"Plan-path alternative {key}: {name}", p(text))
        alts[key] = e
        m.link(e, "relates", m.find("C.0.2", "Asset"))
        m.link(e, "relates", m.find("C.0.6", "Asset"))
    for child, parent in (("B", "A"), ("C", "B"), ("D", "B"), ("E", "B")):
        m.link(alts[child], "relates", alts[parent])
    m.link(alts[selected], "satisfies", req("3.4.2.1"))

    # ---- the decision -------------------------------------------------------------------------------------
    ranking = sorted(a["totals"], key=lambda k: -a["totals"][k]["score"])
    text = ("Decision DEC.1: how the plan path asks the external services (Chapter 11, ADR 0012). Alternatives AL.A to AL.E, criteria EC.1 to EC.6, "
            "swing weight matrix and value scores in the Chapter 11 and 12 report. Scores: "
            + "; ".join(f"{k} {a['totals'][k]['score']:.1f}" for k in ranking)
            + f". Selected: alternative {selected}. Not selected: " + ", ".join(k for k in ranking if k != selected) + ".")
    dec = m.add("dec", t_stmt, "DEC.1", "Decision: dispatch of the plan path", p(text))
    for key in alts:
        m.link(dec, "relates", alts[key])
    for e in crit.values():
        m.link(dec, "relates", e)

    # ---- risks --------------------------------------------------------------------------------------------
    rows = {r["id"]: r for r in a["register"]}
    for rid, r in rows.items():
        cons = band(r["overall_cell"])
        prob = band(r["L"])
        try:
            e = m.find(rid, "Risk")
            for prop, val in (("Probability", prob), ("Consequence", cons)):
                m._set_attr(e, prop, val)
        except SystemExit:
            pass
    new = {
        "TR.16": ("External service answers late and the 3-second display fails",
                  "The forecast and route services are external. On the development laptop every new connection waited about 3.07 s for a name lookup, so a plan that meets a cold connection takes over 3 s (requirement 3.4.2.1) and the weather call misses its 1.0 s limit (5.4.4). Type: performance and availability. Phase: design, test and operations. Handling: mitigate (concurrent dispatch, name cache, deadlines with a labelled fallback; ADR 0012).",
                  ("3.4.2.1", "5.4.4", "5.5.3"), ("F.2.2.3", "F.2.2.4"), ("IO.5",)),
        "TR.17": ("Language model unavailable or too slow",
                  "The optional local language model of C.4 can be stopped, slow or missing. Type: availability. Phase: operations. Handling: fallback built (template text, 2.0 s timeout, 60 s breaker).",
                  ("2.1.10",), ("UC.3.5",), ()),
        "TR.18": ("Untrusted text from a data source reaches the prompt",
                  "A place name, route source or timetable string could carry instructions to the model. Type: security. Phase: design and operations. Handling: guardrail by construction; the prompt is built from the template sentence only.",
                  ("2.1.10",), ("UC.3.5",), ()),
        "TR.19": ("Trip data leaves the machine by a path nobody intended",
                  "A model host set to another machine, or a hosted model, would send trip facts away. Type: security and privacy. Phase: design and operations. Handling: the model client refuses a host that is not loopback.",
                  ("2.5.1", "3.4.5.2"), (), ()),
        "TR.20": ("Response schema drifts between model or server versions",
                  "A new version of the model server could change the shape of its reply. Type: interface. Phase: operations. Handling: a reply without a text field is treated as unavailable.",
                  ("2.1.10",), (), ()),
        "TR.21": ("A dependency is abandoned, relicensed or moved",
                  "The model server, the model weights, the routing host (TR.11), the timetable feed (TR.13) or the web framework may change terms or disappear. Type: supply and legal. Phase: design and operations. Handling: the model is optional and off by default; versions are pinned.",
                  ("2.3.1",), (), ()),
        "TR.22": ("Assistant-written code or text is wrong and merged unreviewed",
                  "Code and text produced with an assistant can be well formed and wrong. Type: process. Phase: design. Handling: prompt log, tests written from the requirement text, human review before merge.",
                  ("2.3.1",), (), ()),
    }
    for rid, (name, text, reqs, acts, ios) in new.items():
        r = rows[rid]
        e = m.add("risk:" + rid, t_risk, rid, name, p(text),
                  {"Status": "Open", "Probability": band(r["L"]), "Consequence": band(r["overall_cell"]),
                   "Consequence Description": text.split(" Type:")[0]})
        for rn in reqs:
            m.link(req(rn), "relates", e)
        for an in acts:
            try:
                m.link(e, "relates", m.find(an, "Action"))
            except SystemExit:
                print("action not found:", an)
        for io in ios:
            try:
                m.link(e, "relates", m.find(io, "Input/Output"))
            except SystemExit:
                print("input/output not found:", io)
        if rid in ("TR.17", "TR.18", "TR.19", "TR.20"):
            m.link(e, "relates", m.find("C.4", "Asset"))
    # the existing risks that the register rates are related to the interactions they come from
    extra = {"TR.4": ("UC.3.5", "UC.1.11"), "TR.11": ("F.2.2.3",)}
    for rid, acts in extra.items():
        for an in acts:
            try:
                m.link(m.find(rid, "Risk"), "relates", m.find(an, "Action"))
            except SystemExit:
                print("action not found:", an)
    ET.indent(m.tree, space="    ")
    m.tree.write(OUT, encoding="utf-8", xml_declaration=False)
    with open(OUT, "r", encoding="utf-8") as f:
        body = f.read()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body)
    return m


if __name__ == "__main__":
    mm = build()
    print(f"wrote {OUT}: {len(mm.new)} new entities")
