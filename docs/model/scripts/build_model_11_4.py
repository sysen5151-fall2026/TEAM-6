"""Build Innoslate model 11.4 from the 11.3 export by adding the two simulation scenarios of Chapter 10.

    python docs/model/scripts/build_model_11_4.py

Reads  docs/model/EcoCommute_11.3_C8-C9_physical_architecture.xml
Writes docs/model/EcoCommute_11.4_C10_simulation.xml

Adds, from docs/ch10/sim/scenarios.py (the single source of the report's diagrams and runs):
  - two parent actions SIM.1 and SIM.2 (the scenarios), each decomposed by its 18 actions t.<k>.<n>;
  - each action is performed by the asset of the model (X.1, C.0.1 ... C.0.6, X.3, X.6), generates one
    input/output and receives the input/outputs it needs; existing input/outputs are reused by name, the
    rest are new;
  - the Duration of each action carries its distribution (Normal mu and sigma, Exponential lambda, seconds), in the format
    Innoslate itself exports; every received input/output is a trigger;
  - every action satisfies the requirement(s) it serves and each new input/output satisfies one (so that Innoslate Intelligence has nothing to flag on them);
  - the parents satisfy the performance requirements the runs are traced to (2.1.1, 2.1.2, 3.4.2.1, 3.4.2.2, 5.5.3).
Nothing of 11.3 is changed or removed. The timeline of each scenario is a parallel group with one branch per asset
(a branch asset), like UC.1 of the model; the two scenarios differ in which input/output triggers which action and in
the order of the actions of C.0.2. Formats of distribution, parallel group, branch asset and trigger were read from an
Innoslate export of the first version of this model. Not yet imported in this form.
"""
import importlib.util
import os
import random
import sys
import uuid
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.dirname(HERE)
SRC = os.path.join(MODEL_DIR, "EcoCommute_11.3_C8-C9_physical_architecture.xml")
OUT = os.path.join(MODEL_DIR, "EcoCommute_11.4_C10_simulation.xml")
sys.path.insert(0, os.path.join(MODEL_DIR, "..", "ch10", "sim"))
import scenarios as S  # noqa: E402

_spec = importlib.util.spec_from_file_location("build_model_10_9", os.path.join(HERE, "build_model_10_9.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

MOP_REQS = ["2.1.1", "2.1.2", "3.4.2.1", "3.4.2.2", "5.5.3"]
# every action satisfies the requirement(s) it serves (Innoslate Intelligence flags an action that satisfies none)
ACTION_REQS = {
    "open": ["2.1.1"], "form": ["2.1.1"], "enter": ["2.1.1"], "submit": ["2.1.1"], "validate": ["2.1.1"],
    "reqroute": ["5.3.7"], "route": ["5.3.8"], "factor": ["5.4.2"], "estimate": ["2.4.2"], "reqwx": ["5.4.3"],
    "wx": ["5.3.2"], "resolve": ["5.4.4"], "recommend": ["2.1.4", "2.1.5"], "present": ["2.1.2", "3.4.2.1"],
    "choose": ["2.1.1"], "record": ["2.1.12"], "display": ["2.1.2", "3.4.2.1"], "review": ["2.1.2"],
}
# the six new input/outputs are satisfied by the requirement of the action that generates them
IO_REQS = {"Planner Request": "2.1.1", "Trip Request": "2.1.1", "Mode Recommendation": "2.1.4", "Comparison View": "2.1.2",
           "Trip Result View": "2.1.2", "Review Note": "2.1.2"}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def find_io(m, name):
    hits = [e for e in m.db.findall("entity") if m.cls(e) == "Input/Output" and e.findtext("name").strip() == name]
    return hits[0] if len(hits) == 1 else None


def set_duration(e, seconds=None, dist=None):
    """Duration in seconds; with dist = ("normal", mu, sigma) or ("exponential", lambda) the Innoslate distribution
    element (format read from an Innoslate export of this model: <distribution><type>NORMAL</type>
    <distributionParameter><name>mu</name><doubleValue>..</doubleValue></distributionParameter> ...)."""
    for a in e:
        if a.tag == "durationAttribute":
            for c in list(a):
                a.remove(c)
            if dist is None:
                ET.SubElement(a, "doubleValue").text = str(seconds)
            else:
                d = ET.SubElement(a, "distribution")
                if dist[0] == "normal":
                    ET.SubElement(d, "type").text = "NORMAL"
                    params = (("mu", dist[1]), ("sigma", dist[2]))
                else:
                    ET.SubElement(d, "type").text = "EXPONENTIAL"
                    params = (("lambda", dist[1]),)
                for n, v in params:
                    dp = ET.SubElement(d, "distributionParameter")
                    ET.SubElement(dp, "name").text = n
                    ET.SubElement(dp, "doubleValue").text = str(v)
            ET.SubElement(a, "units").text = "SECONDS"
            return
    raise SystemExit("no duration attribute on the action template")


TRIGGER_PROP = "I_87AVWCX4Y4J0Q_BZ2QXGHAE6CTJ"   # the Trigger property of the receives / received by relations


def link_trigger(m, kid, io):
    """kid receives io as a trigger: the action waits for it (both directions of the relation carry the flag)."""
    m.link(kid, "receives", io)
    for r in m.db.findall("relationship")[-2:]:
        b = ET.SubElement(r, "booleanAttribute", schemaPropertyId=TRIGGER_PROP)
        ET.SubElement(b, "booleanValue").text = "true"


def branch_timeline(parent, branches, asset_gid):
    """START -> PARALLEL group with one branch per asset (a branch asset), each a serial chain of that asset's actions -> END.
    Same structure as UC.1 of the model: the order between branches comes from the triggers (input/outputs)."""
    sim = parent.find("simulationData")
    for c in list(sim):
        sim.remove(c)
    ET.SubElement(sim, "type").text = "SERIAL"
    gid = parent.findtext("globalId")
    uid = lambda tag: str(uuid.uuid5(uuid.NAMESPACE_URL, gid + tag))
    hexid = lambda tag: uuid.uuid5(uuid.NAMESPACE_URL, gid + "branch" + tag).hex.upper()
    start = ET.SubElement(sim, "controlStructure", id=uid("start"))
    ET.SubElement(start, "type").text = "START"
    group = ET.SubElement(start, "successorStructure", id=uid("group").upper(), group="true")
    ET.SubElement(group, "type").text = "PARALLEL"
    for asset, chain in branches:
        ba = ET.SubElement(group, "branchAsset")
        ET.SubElement(ba, "branchId").text = hexid(asset)
        ET.SubElement(ba, "assetGlobalId").text = asset_gid[asset]
    for asset, chain in branches:
        xb = ET.SubElement(group, "xmlBranch", id=hexid(asset))
        node = ET.SubElement(xb, "controlStructure", id=uid("cs" + asset))
        for i, (kgid, key) in enumerate(chain):
            ET.SubElement(node, "entityGlobalId").text = kgid
            ET.SubElement(node, "type").text = "SERIAL"
            if i < len(chain) - 1:
                node = ET.SubElement(node, "successorStructure", id=uid(f"{asset}-{key}"))
    end = ET.SubElement(group, "successorStructure", id=uid("end"))
    ET.SubElement(end, "type").text = "END"


def fresh_sim(e, chain=None, parent_gid=None):
    old = e.find("simulationData")
    for c in list(old):
        old.remove(c)
    ET.SubElement(old, "type").text = "SERIAL"
    if chain is None:
        return
    new_id = lambda tag: str(uuid.uuid5(uuid.NAMESPACE_URL, parent_gid + tag))
    start = ET.SubElement(old, "controlStructure", id=new_id("start"))
    ET.SubElement(start, "type").text = "START"
    tail = start
    for gid, key in chain:
        step = ET.SubElement(tail, "successorStructure", id=new_id(key))
        ET.SubElement(step, "entityGlobalId").text = gid
        ET.SubElement(step, "type").text = "SERIAL"
        tail = step
    end = ET.SubElement(tail, "successorStructure", id=new_id("end"))
    ET.SubElement(end, "type").text = "END"


def build():
    m = base.Model(SRC)
    m.rng = random.Random(1140)
    t_action = m.find("UC.1.5", "Action")
    t_io = next(e for e in m.db.findall("entity") if m.cls(e) == "Input/Output" and e.findtext("number") == "IO.12")
    asset = {n: m.find(n, "Asset") for n, _, _ in S.ASSETS}
    reqs = [m.find(n, "Requirement") for n in MOP_REQS]
    io_made = {}

    def io(name, desc):
        e = find_io(m, name)
        if e is not None:
            return e
        if name not in io_made:
            io_made[name] = m.add("io:" + name, t_io, "", name, desc)
        return io_made[name]

    summary = {}
    for sc in (1, 2):
        s = S.SCENARIOS[sc]
        parent_key = f"SIM.{sc}"
        parent = m.add(parent_key, t_action, parent_key, f"{s['id']} {s['title']}",
                       f"<p>Simulation scenario {s['id']} of Chapter 10: {esc(s['summary'])} Actions t.{sc}.1 to t.{sc}.18; durations in seconds.</p>")
        set_duration(parent, seconds=0)
        for r in reqs:
            m.link(parent, "satisfies", r)
        kids = []
        acts = S.actions(sc)
        for a in acts:
            desc = (f"<p>Performed by {esc(S.ASSET_NAME[a['asset']])}. Duration: {esc(S.dist_text(a['dist']))}. "
                    f"Rationale: {esc(a['why'])}</p>")
            kid = m.add(a["num"], t_action, a["num"], a["name"], desc)
            set_duration(kid, dist=a["dist"])
            fresh_sim(kid)
            for rn in ACTION_REQS[a["key"]]:
                m.link(kid, "satisfies", m.find(rn, "Requirement"))
            m.link(kid, "decomposes", parent)
            m.link(kid, "performed by", asset[a["asset"]])
            kids.append(kid)
        for a, kid in zip(acts, kids):
            m.link(kid, "generates", io(a["output"], f"<p>Output of {a['num']} {esc(a['name'])} in the Chapter 10 simulation scenarios.</p>"))
        for a, kid in zip(acts, kids):
            for i in a["inputs"]:
                link_trigger(m, kid, io(i, ""))
        # timeline of the parent: one parallel branch per asset, the actions of the asset in listing order
        order = {a["key"]: kid for a, kid in zip(acts, kids)}
        branches = []
        for aid, _, _ in S.ASSETS:
            chain = [(order[k].findtext("globalId"), k) for k in s["order"] if next(a for a in acts if a["key"] == k)["asset"] == aid]
            if chain:
                branches.append((aid, chain))
        branch_timeline(parent, branches, {n: asset[n].findtext("globalId") for n in asset})
        summary[sc] = len(kids)
    for name, rn in IO_REQS.items():
        m.link(io_made[name], "satisfies", m.find(rn, "Requirement"))
    ET.indent(m.tree, space="    ")
    m.tree.write(OUT, encoding="utf-8", xml_declaration=False)
    return m, summary, io_made


if __name__ == "__main__":
    mm, summ, made = build()
    print("actions per scenario:", summ, "| new input/outputs:", len(made), sorted(made))
    print("wrote", OUT)
