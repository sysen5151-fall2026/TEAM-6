"""Physical architecture data for the Chapter 8 + 9 report (EcoCommute, Team 6).

Everything in the report, the figures and the model patch (EcoCommute 11.3) is built
from this one module, so the three cannot drift apart. `check()` verifies the
one-to-one function/asset mapping, that every input/output is carried by a conduit
and that every boundary flow of the decomposed function is accounted for.
"""
from collections import OrderedDict
import mdata as M

# --------------------------------------------------------------------------- top level
SYSTEM = ("C.0", "EcoCommute")
EXTERNAL = OrderedDict([
    ("X.1", "Commuter"), ("X.2", "Pilot Administrator"), ("X.3", "Open-Meteo"),
    ("X.4", "Emission Factor Publisher"), ("X.5", "Hosting Provider"),
])
# added in model 11.0 (use-case level only: no top-level function yet)
EXTRA_EXTERNAL = OrderedDict([("X.6", "Route Service"), ("X.7", "Transit Schedule Publisher")])
CTX_EXTRA = [("Route request", "X.6", ["Route Request"]), ("Route response", "X.6", ["Route Options"]), ("Transit schedule", "X.7", ["Bus Schedule"])]
# top-level function -> mechanism (unchanged from the Metafunction of model 10.8)
TOP_MECH = {"F.1": "X.1", "F.2": "C.0", "F.3": "X.2", "F.4": "X.3", "F.5": "X.4", "F.6": "X.5"}

# --------------------------------------------------------------------------- first level
# function id -> (asset id, asset name, short name for diagrams, what it is made of)
ASSET1 = OrderedDict([
    ("F.2.0", ("C.0.0", "Operations Subsystem", "Operations",
               "Release package and deployment scripts, availability probe and alert rules, retirement runbook, pilot operations staff.")),
    ("F.2.1", ("C.0.1", "Entry Subsystem", "Entry",
               "Responsive web entry form, input validation rules, consent check, deletion-request handler.")),
    ("F.2.2", ("C.0.2", "Reference Data Subsystem", "Reference Data",
               "Reviewed emission-factor store with version control, factor selection logic, Open-Meteo client and forecast matching.")),
    ("F.2.3", ("C.0.3", "Estimation Subsystem", "Estimation",
               "Calculation engine for CO2e, distance convention, always-drive baseline rule and method disclosure text.")),
    ("F.2.4", ("C.0.4", "Records Subsystem", "Records",
               "Trip record database, access control, weekly/monthly trend aggregation, deletion and retention jobs.")),
    ("F.2.5", ("C.0.5", "Recommendation Subsystem", "Recommendation",
               "Rule set on distance, forecast weather and feasibility settings; one alternative with a stated reason.")),
    ("F.2.6", ("C.0.6", "Presentation Subsystem", "Presentation",
               "Result assembly, plain-language explanation model (restates calculated facts only), responsive result view.")),
    ("F.2.7", ("C.0.7", "Reporting Subsystem", "Reporting",
               "Aggregation, small-group suppression, authenticated dashboard and approved aggregate export.")),
])
FOR_FUNC = {f: v[0] for f, v in ASSET1.items()}                  # F.2.x -> C.0.x
ASSET_NAME = {v[0]: v[1] for v in ASSET1.values()}
ASSET_SHORT = {v[0]: v[2] for v in ASSET1.values()}
FUNC_OF = {v[0]: f for f, v in ASSET1.items()}
for _x, _n in EXTERNAL.items():
    ASSET_NAME[_x] = _n
    ASSET_SHORT[_x] = _n
ASSET_NAME["C.0"] = "EcoCommute"
A1 = [v[0] for v in ASSET1.values()]                              # C.0.0 .. C.0.7 in diagonal order

# --------------------------------------------------------------------------- the decomposed function
DECOMP_F = "F.2.2"            # Manage Reference Data
DECOMP_A = "C.0.2"            # Reference Data Subsystem

# new internal input/outputs at the second level
IO2 = OrderedDict([
    ("IO.23", ("Versioned Factor Set", "Reviewed factor values stored with source, units, geography, methodology and version; the reference the selection step reads.")),
    ("IO.24", ("Forecast Query Context", "Coarse location and trip hour of the pending weather request; tells the forecast step which part of the response is the trip's forecast.")),
])
IO_ALL = dict(M.IO)
IO_ALL.update({k: v[0] for k, v in IO2.items()})

# second-level functions: id -> (name, asset id, asset name, composition)
FUNC2 = OrderedDict([
    ("F.2.2.1", ("Load Emission Factors", "C.0.2.1", "Factor Import Module",
                 "Reads a published factor file or source document, rejects sets that lack source, units, geography, methodology or version, and stores the accepted set under a new version.")),
    ("F.2.2.2", ("Select Emission Factor", "C.0.2.2", "Factor Lookup Module",
                 "Chooses the applicable factor for the trip mode and geography from the versioned set and returns it with its provenance.")),
    ("F.2.2.3", ("Request Weather Forecast", "C.0.2.3", "Weather Client Module",
                 "Builds the HTTPS request from the coarse area and trip time only, sends it to Open-Meteo with a timeout.")),
    ("F.2.2.4", ("Resolve Trip Forecast", "C.0.2.4", "Forecast Resolver Module",
                 "Picks the forecast hour that matches the trip, keeps the forecast timestamp and flags a missing or late response.")),
])
FOR_FUNC2 = {f: v[1] for f, v in FUNC2.items()}
ASSET2 = OrderedDict((v[1], (v[2], f)) for f, v in FUNC2.items())
for _a, (_n, _f) in ASSET2.items():
    ASSET_NAME[_a] = _n
    ASSET_SHORT[_a] = _n.replace(" Module", "")
A2 = list(ASSET2)

# second-level flows: io -> (sources, [(dest, role)]), "ENV" = outside F.2.2.  role I/C/O
L2FLOW = {
    "IO.5": (["ENV"], [("F.2.2.4", "I")]),
    "IO.6": (["ENV"], [("F.2.2.1", "C")]),
    "IO.12": (["ENV"], [("F.2.2.2", "I"), ("F.2.2.3", "I")]),
    "IO.4": (["F.2.2.3"], [("ENV", "O")]),
    "IO.14": (["F.2.2.2"], [("ENV", "O")]),
    "IO.15": (["F.2.2.4"], [("ENV", "O")]),
    "IO.23": (["F.2.2.1"], [("F.2.2.2", "C")]),
    "IO.24": (["F.2.2.3"], [("F.2.2.4", "C")]),
}
BOUNDARY = ["IO.5", "IO.6", "IO.12", "IO.4", "IO.14", "IO.15"]    # first-level flows of F.2.2
L2_INTERNAL = ["IO.23", "IO.24"]
L2ORDER = list(FUNC2)

# --------------------------------------------------------------------------- conduits (interfaces)
# id, name, endpoint A, endpoint B (info flows A->B unless both directions listed), io list, medium
INT_MED = "internal service API"
CONDUITS1 = [
    # external-facing (the names of the context-level conduits are kept)
    ("K.1", "Trip details", "X.1", "C.0.1", ["IO.1", "IO.2", "IO.3"], "responsive web entry form over HTTPS"),
    ("K.2", "Result and advice", "C.0.6", "X.1", ["IO.3"], "responsive web result view over HTTPS"),
    ("K.3", "Consent record", "X.1", "C.0.4", ["IO.2"], "consent and account settings page over HTTPS"),
    ("K.4", "Feasibility settings", "X.1", "C.0.5", ["IO.2"], "feasibility settings page over HTTPS"),
    ("K.5", "Weather query", "C.0.2", "X.3", ["IO.4"], "HTTPS API request"),
    ("K.6", "Forecast", "X.3", "C.0.2", ["IO.5"], "structured HTTPS API response"),
    ("K.7", "Reviewed factors", "X.4", "C.0.2", ["IO.6"], "reviewed file or source-document ingestion"),
    ("K.8", "Summary request", "X.2", "C.0.7", ["IO.7", "IO.9"], "authenticated dashboard"),
    ("K.9", "Approved aggregates", "C.0.7", "X.2", ["IO.8"], "authenticated dashboard and approved aggregate export"),
    ("K.10", "Pilot rules", "X.2", "C.0.0", ["IO.9"], "authenticated dashboard"),
    ("K.11", "Hosting service", "C.0.0", "X.5", ["IO.10", "IO.11"], "provider deployment and status interface"),
    # internal
    ("K.12", "Entry to reference data", "C.0.1", "C.0.2", ["IO.12"], INT_MED),
    ("K.13", "Entry to estimation", "C.0.1", "C.0.3", ["IO.12"], INT_MED),
    ("K.14", "Entry to records", "C.0.1", "C.0.4", ["IO.12", "IO.13"], INT_MED),
    ("K.15", "Entry to recommendation", "C.0.1", "C.0.5", ["IO.12"], INT_MED),
    ("K.16", "Factor record", "C.0.2", "C.0.3", ["IO.14"], INT_MED),
    ("K.17", "Trip forecast", "C.0.2", "C.0.5", ["IO.15"], INT_MED),
    ("K.18", "Estimate to records", "C.0.3", "C.0.4", ["IO.16"], INT_MED),
    ("K.19", "Estimate to presentation", "C.0.3", "C.0.6", ["IO.16", "IO.17"], INT_MED),
    ("K.20", "Trend feed", "C.0.4", "C.0.6", ["IO.18"], INT_MED),
    ("K.21", "Record extract", "C.0.4", "C.0.7", ["IO.19"], "read-only query interface"),
    ("K.22", "Recommendation feed", "C.0.5", "C.0.6", ["IO.20"], INT_MED),
    ("K.23", "Retention link", "C.0.0", "C.0.4", ["IO.21"], "scheduled retention job interface"),
    ("K.24", "Status feed", "C.0.0", "C.0.7", ["IO.22"], "service log feed"),
]
# second-level internal conduits (inside C.0.2)
CONDUITS2 = [
    ("K.2.1", "Factor set access", "C.0.2.1", "C.0.2.2", ["IO.23"], "read access to the versioned factor store"),
    ("K.2.2", "Query context", "C.0.2.3", "C.0.2.4", ["IO.24"], "in-process query handoff"),
]
# second-level boundary interfaces: first-level conduit that is re-attached to a module
BOUNDARY2 = [
    ("K.7", "X.4", "C.0.2.1", "IO.6"), ("K.12", "C.0.1", "C.0.2.2", "IO.12"),
    ("K.12", "C.0.1", "C.0.2.3", "IO.12"), ("K.16", "C.0.2.2", "C.0.3", "IO.14"),
    ("K.5", "C.0.2.3", "X.3", "IO.4"), ("K.6", "X.3", "C.0.2.4", "IO.5"),
    ("K.17", "C.0.2.4", "C.0.5", "IO.15"),
]
INTERNAL_IDS = [c[0] for c in CONDUITS1[11:]]
EXTERNAL_IDS = [c[0] for c in CONDUITS1[:11]]

# --------------------------------------------------------------------------- UC.1 sequence over assets
# (step, interaction name, sender asset, [receiver assets], io, UC.1 action, kind)
def _a(f):
    if f in M.TOP:                       # top level function -> its external asset
        return TOP_MECH[f]
    return FOR_FUNC[f]


SEQ1 = []
for _s in M.SEQ:
    n, name, snd, rcv, io, uc, kind = _s
    SEQ1.append((n, name, _a(snd) if snd != "F.1" else "X.1", [_a(r) if r != "F.1" else "X.1" for r in rcv], io, uc, kind))

# second-level scenario: steps of UC.1 that touch the Reference Data Subsystem
# (step, name, sender, [receivers], io, UC.1 action, kind)
SEQ2 = [
    ("1", "Reviewed Emission Factors", "X.4", ["C.0.2.1"], "IO.6", "precondition", "ext"),
    ("1.1", "Versioned Factor Set", "C.0.2.1", ["C.0.2.2"], "IO.23", "precondition", "int"),
    ("2", "Validated Commute Entry", "C.0.1", ["C.0.2.2", "C.0.2.3"], "IO.12", "UC.1.5", "ext"),
    ("3", "Emission Factor Record", "C.0.2.2", ["C.0.3"], "IO.14", "UC.1.5", "ext"),
    ("4", "Weather Request", "C.0.2.3", ["X.3"], "IO.4", "UC.1.6", "ext"),
    ("4.1", "Forecast Query Context", "C.0.2.3", ["C.0.2.4"], "IO.24", "UC.1.6", "int"),
    ("5", "Weather Forecast Data", "X.3", ["C.0.2.4"], "IO.5", "UC.1.7", "ext"),
    ("6", "Trip Weather Forecast", "C.0.2.4", ["C.0.5"], "IO.15", "UC.1.7", "ext"),
]

# --------------------------------------------------------------------------- complexity of the first-level functions
def complexity():
    """(function, name, unique IO, internal partners, external systems, UC.1 steps, score)."""
    rows = []
    for f, name in M.L1:
        ios, pint, pext = set(), set(), set()
        for io, (srcs, dests) in M.L1FLOW.items():
            touched = f in srcs or any(d == f for d, _ in dests)
            if not touched:
                continue
            ios.add(io)
            others = [d for d, _ in dests] if f in srcs else [x for x in srcs]
            for o in others:
                if o == "ENV":
                    sf, df, _ = M.META[io]
                    pext.add(TOP_MECH[df] if f in srcs else TOP_MECH[sf])
                else:
                    pint.add(o)
        uc = sum(1 for s in M.SEQ if s[2] == f or f in s[3])
        rows.append((f, name, len(ios), len(pint), len(pext), uc, len(ios) + len(pint) + len(pext) + uc))
    return rows


# --------------------------------------------------------------------------- non-functional allocation
# system-wide requirement -> {asset: "P" primary | "C" contributes}
NFR = OrderedDict([
    ("3.4.1.1", ("cost no more than $750,000", {a: "C" for a in A1})),
    ("3.4.1.2", ("report results before December 18, 2026", {"C.0.7": "P", "C.0.4": "C", "C.0.0": "C", "C.0.2": "C"})),
    ("3.4.2.1", ("display each trip result within 3 seconds", {"C.0.1": "C", "C.0.2": "P", "C.0.3": "C", "C.0.4": "C", "C.0.5": "C", "C.0.6": "P"})),
    ("3.4.2.2", ("complete entry in 30 seconds or less", {"C.0.1": "P"})),
    ("3.4.3.1", ("availability of at least 99.5 percent", {"C.0.0": "P", "C.0.1": "C", "C.0.2": "C", "C.0.3": "C", "C.0.4": "C", "C.0.5": "C", "C.0.6": "C"})),
    ("3.4.3.2", ("operate with at least 500 enrolled accounts", {"C.0.1": "C", "C.0.2": "C", "C.0.3": "C", "C.0.4": "P", "C.0.5": "C", "C.0.6": "C", "C.0.7": "C"})),
    ("3.4.4.1", ("conform to WCAG 2.2 Level AA", {"C.0.1": "P", "C.0.6": "P"})),
    ("3.4.5.1", ("restrict access to individual trip records", {"C.0.4": "P", "C.0.1": "C", "C.0.7": "C"})),
    ("3.4.5.2", ("store only coarse location, no device traces", {"C.0.1": "P", "C.0.2": "C", "C.0.4": "C"})),
    ("3.4.5.3", ("suppress aggregate groups below 5", {"C.0.7": "P"})),
    ("3.4.6.1", ("reproduce reference cases to the nearest gram", {"C.0.3": "P", "C.0.2": "C"})),
    ("3.4.5.4", ("send the Route Service only the entered places", {"C.0.2": "P", "C.0.1": "C"})),
    ("3.4.5.5", ("store passwords and invite codes only as hashes", {"C.0.4": "P"})),
    ("3.4.5.6", ("lock log-in after repeated wrong passwords", {"C.0.4": "P", "C.0.1": "C"})),
    ("3.4.5.7", ("keep no record of who asked in the place cache", {"C.0.2": "P", "C.0.4": "C"})),
    ("3.4.6.2", ("label route-based figures as estimates", {"C.0.3": "P", "C.0.6": "P"})),
    ("3.4.6.3", ("state that bus times come from a timetable", {"C.0.5": "P", "C.0.6": "C"})),
])

# --------------------------------------------------------------------------- walking-skeleton modules (code view)
OLD_MODULES = [
    ("C.1", "Web Front End", "C.0.1 Entry (entry form), C.0.6 Presentation (result view)"),
    ("C.2", "Application Service", "C.0.3 Estimation, C.0.5 Recommendation, C.0.4 Records (trend logic)"),
    ("C.3", "Data Adapter", "C.0.2 Reference Data (factor store, weather access), C.0.4 Records (trip store)"),
    ("C.4", "Explanation Model", "C.0.6 Presentation (explanation step)"),
]

# --------------------------------------------------------------------------- physical alternatives
CRITERIA = [   # name, weight, why
    ("Function-to-form fit", 25, "Chapter 8 rule: every first-level function is performed by exactly one asset and the physical hierarchy mirrors the functional one."),
    ("Requirement allocation", 20, "Each system requirement can be allocated to and verified against one named asset (3.3.1.x and 3.4.x)."),
    ("Interface simplicity", 15, "Fewer and clearer conduits to specify and test; lower coupling."),
    ("Privacy and access separation", 15, "Trip records and aggregates sit in assets that can be access-controlled apart (3.4.5.1 to 3.4.5.3)."),
    ("Cost and schedule control", 15, "A budget and a due date can be apportioned to each asset (3.4.1.1, 3.4.1.2)."),
    ("Reuse of walking skeleton", 10, "Share of the Chapter 2 code and tests that the structure keeps."),
]
ALTS = OrderedDict([
    ("A", ("Functional subsystems (eight)", "One subsystem per first-level function: C.0.0 to C.0.7.", [5, 5, 3, 5, 4, 3])),
    ("B", ("Walking-skeleton modules (four)", "C.1 Web Front End, C.2 Application Service, C.3 Data Adapter, C.4 Explanation Model under C.0.", [2, 2, 5, 2, 2, 5])),
    ("C", ("Three-tier layers (five)", "Web tier, service tier, data tier, plus operations and reporting assets.", [3, 3, 4, 3, 3, 4])),
])
ALT_NOTES = {
    "A": "Matches F.2.0 to F.2.7 one to one. Costs the most interfaces (24 conduits) and needs a thin adapter to the existing code layout.",
    "B": "Few interfaces, but C.1 and C.4 each serve two functions, C.2 and C.3 cross F.2.3 to F.2.5 and F.2.2 to F.2.4, and F.2.0 and F.2.7 have no asset. It cannot satisfy the one-to-one rule or give a clean budget per asset.",
    "C": "Layers group by technology, not function: the service tier performs six functions, so requirement allocation and cost apportionment stay coarse. Operations and reporting still need their own assets.",
}


# --------------------------------------------------------------------------- consistency checks
def check():
    problems = []
    # 1. one function, one asset, one asset per function
    if len(set(FOR_FUNC.values())) != len(M.L1):
        problems.append("first-level asset mapping is not one to one")
    if [f for f, _ in M.L1] != list(ASSET1):
        problems.append("first-level function list and asset list differ")
    # 2. every first-level IO is carried by a conduit between the right assets
    cmap = {}
    for cid, name, a, b, ios, med in CONDUITS1:
        for io in ios:
            cmap.setdefault(io, []).append((a, b))

    def asset_of(x):
        return x

    ext_of = {}
    for io, (s, d, r) in M.META.items():
        ext_of[io] = (TOP_MECH[s], TOP_MECH[d])
    for io, (srcs, dests) in M.L1FLOW.items():
        for s in srcs:
            for d, _ in dests:
                if s == "ENV" and d == "ENV":
                    continue
                if s == "ENV":
                    sa, da = ext_of[io][0], FOR_FUNC[d]
                elif d == "ENV":
                    sa, da = FOR_FUNC[s], ext_of[io][1]
                else:
                    sa, da = FOR_FUNC[s], FOR_FUNC[d]
                if not any({sa, da} == {x, y} for x, y in cmap.get(io, [])):
                    problems.append(f"{io}: no conduit {sa}-{da}")
    for io, pairs in cmap.items():
        if io not in M.IO:
            problems.append(f"{io} unknown")
    # 3. second-level boundary
    for io in BOUNDARY:
        if io not in L2FLOW:
            problems.append(f"{io} missing at second level")
    for io, (srcs, dests) in L2FLOW.items():
        for s in srcs:
            if s != "ENV" and s not in FUNC2:
                problems.append(f"{io} source {s}")
        for d, _ in dests:
            if d != "ENV" and d not in FUNC2:
                problems.append(f"{io} dest {d}")
    # first-level flows of F.2.2 versus second-level boundary
    first = {}
    for io, (srcs, dests) in M.L1FLOW.items():
        if DECOMP_F in srcs:
            first[io] = "out"
        if any(d == DECOMP_F for d, _ in dests):
            first[io] = "in"
    if set(first) != set(BOUNDARY):
        problems.append(f"boundary mismatch {sorted(first)} vs {sorted(BOUNDARY)}")
    for io, (srcs, dests) in L2FLOW.items():
        if io in BOUNDARY:
            direction = "in" if "ENV" in srcs else "out"
            if first[io] != direction:
                problems.append(f"{io} direction")
    return problems


if __name__ == "__main__":
    p = check()
    print("OK" if not p else p)
    print(len(CONDUITS1), "first-level conduits;", len(INTERNAL_IDS), "internal;", len(EXTERNAL_IDS), "external")
    for r in complexity():
        print(r)
    for k, (n, d, sc) in ALTS.items():
        print(k, n, sum(w * s for (_, w, _), s in zip(CRITERIA, sc)) / 100)
