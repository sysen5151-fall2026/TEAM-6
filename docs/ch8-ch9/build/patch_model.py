"""Builds Innoslate export EcoCommute_11.3_C8-C9_physical_architecture.xml from the 11.0 export.

Adds: eight first-level assets C.0.0-C.0.7 (one per F.2.0-F.2.7), four second-level
modules C.0.2.1-C.0.2.4, second-level functions F.2.2.1-F.2.2.4, input/outputs IO.23-IO.24,
conduits K.1-K.24 and K.2.1-K.2.2 with `transfers`, `performed by` allocations, the
system design output requirements document (4), the Reference Data Subsystem component
specification (5), and `satisfied by C.0` on the leaf system-wide requirements.
The walking-skeleton modules C.1-C.4 are detached from C.0 and kept for code traceability.
Not import-tested in Innoslate; import into a copy of the project first.
"""
import copy
import json
import random
import string
import sys
import uuid
from datetime import datetime, timezone
from lxml import etree

import mdata as M
import pdata as P
import reqdata as Q

SRC = sys.argv[1]
DST = sys.argv[2]
random.seed(1051)
tree = etree.parse(SRC)
root = tree.getroot()
sch = root.find("schema")
db = root.find("database")
CLS = {c.findtext("name"): c.get("id") for c in sch.iter("schemaClass")}
REL = {c.findtext("name"): c for c in sch.iter("schemaRelation")}
RELID = {n: c.get("id") for n, c in REL.items()}
INV = {n: next(k for k, v in REL.items() if v.get("id") == c.findtext("inverseRelationId")) for n, c in REL.items()}
TRIGGER = "I_87AVWCX4Y4J0Q_BZ2QXGHAE6CTJ"
ORIGIN = "I_1DTFF1DF8WKMC_9FMWMQBECVJZ8"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

ENT = {e.findtext("globalId"): e for e in db.findall("entity")}
BYNUM = {}
for g, e in ENT.items():
    n = e.findtext("number")
    if n:
        BYNUM.setdefault(n, g)
BYNAME = {}
for g, e in ENT.items():
    BYNAME.setdefault(e.findtext("name"), g)
next_id = max(int(e.get("id")) for e in db.findall("entity")) + 1
first_rel = db.find("relationship")


def gid():
    a = "".join(random.choices(string.ascii_uppercase + string.digits, k=14))
    b = "".join(random.choices(string.ascii_uppercase + string.digits, k=random.choice([12, 13])))
    return f"I_{a}_{b}"


def template(cls_name, num):
    return copy.deepcopy(ENT[BYNUM[num]]) if num else None


TEMPL = {"Asset": "C.0", "Action": "F.2.7", "Input/Output": "IO.9", "Requirement": "3.3.1.2"}
TEMPL_CACHE = {k: copy.deepcopy(ENT[BYNUM[v]]) for k, v in TEMPL.items()}
TEMPL_CACHE["Conduit"] = copy.deepcopy(ENT[BYNAME["Weather query"]])
TEMPL_CACHE["Artifact"] = copy.deepcopy(ENT[BYNAME["EcoCommute System Requirements Document (SysRD)"]])
CREATED = {}


def new_entity(cls, name, number, desc=""):
    global next_id
    e = copy.deepcopy(TEMPL_CACHE[cls])
    e.set("id", str(next_id))
    next_id += 1
    e.find("name").text = name
    e.find("description").text = desc
    e.find("number").text = number
    g = gid()
    e.find("globalId").text = g
    e.find("createdOn").text = NOW
    e.find("modifiedOn").text = NOW
    for cs in e.iter("controlStructure", "successorStructure"):
        cs.set("id", str(uuid.uuid4()))
    # tidy template-specific content
    for tag in ("metadata", "imageId", "labelId"):
        for x in e.findall(tag):
            e.remove(x)
    db.insert(list(db).index(first_rel), e)
    ENT[g] = e
    if number:
        BYNUM[number] = g
    CREATED[number or name] = g
    return g


def set_attr(e, prop_id, text):
    for sa in e.findall("stringAttribute"):
        if sa.get("schemaPropertyId") == prop_id:
            sa.find("value").text = text


def relate(src, rel, dst, bool_val=None):
    """Adds src --rel--> dst and the inverse. Skips duplicates."""
    for (a, r, b, v) in ((src, rel, dst, bool_val), (dst, INV[rel], src, bool_val)):
        dup = False
        for x in db.findall("relationship"):
            if x.findtext("sourceId") == a and x.findtext("targetId") == b and x.findtext("schemaRelationId") == RELID[r]:
                dup = True
                break
        if dup:
            continue
        x = etree.Element("relationship")
        etree.SubElement(x, "sourceId").text = a
        etree.SubElement(x, "schemaRelationId").text = RELID[r]
        etree.SubElement(x, "targetId").text = b
        if v is not None:
            pid = TRIGGER if rel in ("receives", "received by") else ORIGIN
            ba = etree.SubElement(x, "booleanAttribute")
            ba.set("schemaPropertyId", pid)
            etree.SubElement(ba, "booleanValue").text = "true" if v else "false"
        db.append(x)


def unrelate(a_num, rel, b_num):
    a, b = BYNUM[a_num], BYNUM[b_num]
    n = 0
    for x in list(db.findall("relationship")):
        s, t, r = x.findtext("sourceId"), x.findtext("targetId"), x.findtext("schemaRelationId")
        if (s, t, r) in ((a, b, RELID[rel]), (b, a, RELID[INV[rel]])):
            db.remove(x)
            n += 1
    return n


def N(num):
    return BYNUM[num]


# ---------------------------------------------------------------- 1. detach walking-skeleton modules from C.0
# Their `performs` links stay: tests/test_model_linkage.py reads the performers of UC.3 and UC.4 from them.
removed = 0
for old, _, _ in P.OLD_MODULES:
    removed += unrelate("C.0", "decomposed by", old)
    ENT[N(old)].find("description").text = ("Walking-skeleton implementation module (code view, ADR 0001). Not a first-level asset of the form architecture; "
                                           "it implements parts of: " + dict((a, c) for a, _, c in P.OLD_MODULES)[old] + ".")

# ---------------------------------------------------------------- 2. first-level assets
for f, (aid, an, short, comp) in P.ASSET1.items():
    g = new_entity("Asset", an, aid, f"First-level subsystem that performs {f} {M.L1NAME[f]}. Made of: {comp}")
    relate(g, "decomposes", N("C.0"))
    relate(N(f), "performed by", g)

# ---------------------------------------------------------------- 3. second level
for io, (name, d) in P.IO2.items():
    new_entity("Input/Output", name, io, d)
for f, (name, aid, an, comp) in P.FUNC2.items():
    ga = new_entity("Asset", an, aid, f"Second-level module of C.0.2 that performs {f} {name}. {comp}")
    relate(ga, "decomposes", N("C.0.2"))
    gf = new_entity("Action", name, f, comp)
    relate(gf, "decomposes", N("F.2.2"))
    relate(gf, "performed by", ga)
ctrl = lambda role: role == "C"
for io, (srcs, dests) in P.L2FLOW.items():
    for s in srcs:
        if s != "ENV":
            relate(N(s), "generates", N(io))
    for d, role in dests:
        if d != "ENV":
            relate(N(d), "receives", N(io), bool_val=(role == "C"))

def set_chain(parent_num, child_nums):
    sim = ENT[N(parent_num)].find("simulationData")
    for old in sim.findall("controlStructure"):
        sim.remove(old)
    start = etree.SubElement(sim, "controlStructure", id=str(uuid.uuid4()))
    etree.SubElement(start, "type").text = "START"
    cur = start
    for c in child_nums:
        nxt = etree.SubElement(cur, "successorStructure", id=str(uuid.uuid4()))
        etree.SubElement(nxt, "entityGlobalId").text = N(c)
        etree.SubElement(nxt, "type").text = "SERIAL"
        cur = nxt
    end = etree.SubElement(cur, "successorStructure", id=str(uuid.uuid4()))
    etree.SubElement(end, "type").text = "END"


set_chain("F.2.2", list(P.FUNC2))

# ---------------------------------------------------------------- 4. UC.1 performers
alloc = {"UC.1.2": ["C.0.1"], "UC.1.5": ["C.0.1", "C.0.2"], "UC.1.6": ["C.0.2"], "UC.1.8": ["C.0.3", "C.0.4"],
         "UC.1.9": ["C.0.4", "C.0.3"], "UC.1.10": ["C.0.5"], "UC.1.11": ["C.0.6"]}
for uc, assets in alloc.items():
    for a in assets:
        relate(N(uc), "performed by", N(a))

# ---------------------------------------------------------------- 5. conduits
for cid, name, a, b, ios, med in P.CONDUITS1 + P.CONDUITS2:
    ga = N(a) if a in BYNUM else None
    gb = N(b)
    g = new_entity("Conduit", name, cid, f"<p>Medium: {med}. Connects {P.ASSET_NAME.get(a, a)} ({a}) with {P.ASSET_NAME.get(b, b)} ({b}).</p>")
    relate(g, "connects to", ga, bool_val=True)
    relate(g, "connects to", gb, bool_val=False)
    for io in ios:
        relate(g, "transfers", N(io))

# ---------------------------------------------------------------- 6. requirements
SYS_DOC_ART = BYNAME["EcoCommute System Requirements Document (SysRD)"]


def rationale_text(r, extra=""):
    t = f"Rationale: {r['rat']}\nMOP: {r['mop']}\nVerification criteria: {r['ver']} Method: {r['method']}.\nStakeholder requirements: {', '.join(r['stk'])}"
    if r.get("flow"):
        t += f"\nFlow-down method: {r['flow']}"
    return t + extra


RAT_PROP = "I_A0A1JA8828HXR_BNPNE83S7ACG4"
meta = {}


def make_doc(root_t, headers, leaves_by_hdr, art_name, art_desc):
    num, name, desc = root_t
    rg = new_entity("Requirement", name, num, desc)
    set_attr(ENT[rg], RAT_PROP, "")
    order = [(0, rg)]
    for hnum, hname, hdesc in headers:
        hg = new_entity("Requirement", hname, hnum, hdesc)
        set_attr(ENT[hg], RAT_PROP, "")
        relate(hg, "decomposes", rg)
        order.append((1, hg))
        for r in leaves_by_hdr[hnum]:
            lg = new_entity("Requirement", r["name"], r["num"], r["stmt"])
            set_attr(ENT[lg], RAT_PROP, rationale_text(r))
            relate(lg, "decomposes", hg)
            order.append((2, lg))
            for p in r["parents"]:
                relate(lg, "traced from", N(p))
            for s in r["stk"]:
                if s in BYNUM:
                    pass
            relate(lg, "satisfied by", N(r["asset"]))
            if r.get("func"):
                relate(lg, "satisfied by", N(r["func"]))
    ag = new_entity("Artifact", art_name, "", art_desc)
    relate(ag, "source of", rg)
    ENT[ag].find("number").text = None
    md = etree.Element("metadata")
    ENT[ag].insert(list(ENT[ag]).index(ENT[ag].find("modifiedOn")) + 1, md)
    etree.SubElement(md, "name").text = "documents:meta"
    etree.SubElement(md, "value").text = json.dumps([{"level": float(l), "entityId": float(ENT[g].get("id")), "metaNumber": ""} for l, g in order], separators=(",", ":"))
    return rg


make_doc(Q.DOC4, Q.DOC4_HDR, {"4.1": Q.SDOR}, "EcoCommute System Design Output Requirements Document (SDOR)",
         "Design output requirements for the leaf first-level functions, stated against the subsystems that perform them.")
make_doc(Q.DOC5, Q.DOC5_HDR, {"5.1": Q.INPUT, "5.2": Q.OUTPUT, "5.3": Q.INTERFACE, "5.4": Q.FUNCTIONAL, "5.5": Q.SYSWIDE},
         "Reference Data Subsystem Component Specification (CompSpec)",
         "Component requirements for C.0.2 Reference Data Subsystem, kept apart from the system requirements.")
# stakeholder tracing of design output requirements
for r in Q.SDOR + Q.INPUT + Q.OUTPUT + Q.INTERFACE + Q.FUNCTIONAL + Q.SYSWIDE:
    for s in r["stk"]:
        if s in BYNUM and r["num"] in BYNUM:
            relate(N(r["num"]), "traced from", N(s))

# input/outputs and conduits must satisfy a requirement (Innoslate Intelligence)
for io, reqs in {"IO.23": ["3.3.1.2", "5.4.1", "5.4.2"], "IO.24": ["3.3.1.2", "5.4.3", "5.4.4"]}.items():
    for rq in reqs:
        relate(N(rq), "satisfied by", N(io))
CSAT = {"K.1": "3.2.1", "K.2": "3.2.2", "K.3": "3.2.1", "K.4": "3.2.1", "K.5": "3.2.3", "K.6": "3.2.4", "K.7": "3.2.5", "K.8": "3.2.6",
        "K.9": "3.2.7", "K.10": "3.2.6", "K.11": "3.2.8", "K.12": "5.3.4", "K.13": "3.3.1.3", "K.14": "3.3.1.4", "K.15": "3.3.1.5",
        "K.16": "5.3.5", "K.17": "5.3.6", "K.18": "3.3.1.4", "K.19": "3.3.1.6", "K.20": "3.3.1.6", "K.21": "3.3.1.7", "K.22": "3.3.1.6",
        "K.23": "3.3.1.8", "K.24": "3.3.1.7", "K.2.1": "5.4.2", "K.2.2": "5.4.4"}
for k, rq in CSAT.items():
    relate(N(k), "satisfies", N(rq))

# the Metafunction is performed by the Universe, so the top-level mechanisms hang from it (no tunnels on the Metafunction IDEF0)
relate(N("F.0"), "performed by", N("0"))

# ---------------------------------------------------------------- 7. leaf system-wide requirements satisfied by the system asset
leafs = [n for n in BYNUM if n.startswith("3.4.") and n.count(".") == 3]
for n in leafs:
    relate(N(n), "satisfied by", N("C.0"))

# ---------------------------------------------------------------- results date moved to December 18, 2026
for e in ENT.values():
    if e.findtext("number") in ("3.4.1.2", "2.3.4"):
        for node in e.iter("name", "description", "value"):
            if node.text and "June 30, 2027" in node.text:
                node.text = node.text.replace("June 30, 2027", "December 18, 2026")

# stakeholder requirement 2.1.6: pilot of four weeks instead of eight
for e in ENT.values():
    if e.findtext("number") == "2.1.6":
        for node in e.iter("name", "description", "value"):
            if node.text:
                node.text = node.text.replace("after eight weeks", "after four weeks").replace("week eight", "week four")

# ---------------------------------------------------------------- write
root.find("labels")  # unchanged
tree.write(DST, xml_declaration=True, encoding="UTF-8", pretty_print=True)
print(f"entities added: {len(CREATED)}; relationships removed: {removed}; system-wide leaves traced to C.0: {len(leafs)}")
