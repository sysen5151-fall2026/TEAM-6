"""Build Innoslate model 11.0 from the 10.9 export by adding what the app gained after 10.9.

    python -I docs/model/scripts/build_model_11_0.py

Reads  docs/model/EcoCommute_10.9_web_flow.xml
Writes docs/model/EcoCommute_11.0_accounts_transit.xml

After 10.9 the app gained: the TCAT bus schedule from the published GTFS feed (ADR 0007), vehicles
the Commuter has and a carpool share (ADR 0006, 0008), place suggestions while typing, and
invite-only accounts with saved trips (ADR 0009). 11.0 models them. Only two descriptions of 10.9
are changed (2.1.11 and 3.3.1.9, which still said the bus time is typed); everything else is kept
and every relationship is written in both directions, as Innoslate exports them. The file is named
11.0, not 10.10, so that a plain sort of the export names still ends with the newest one.

Not imported into Innoslate yet: see docs/model/11.0-changes.md.
"""

import importlib.util
import os
import random
import sys
import uuid
from collections import Counter
import xml.etree.ElementTree as ET
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.dirname(HERE)
SRC = os.path.join(MODEL_DIR, "EcoCommute_10.9_web_flow.xml")
OUT = os.path.join(MODEL_DIR, "EcoCommute_11.0_accounts_transit.xml")

_spec = importlib.util.spec_from_file_location("build_model_10_9", os.path.join(HERE, "build_model_10_9.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
QUALITY = base.QUALITY

CHANGED = {  # existing description -> new description, with the reason in docs/model/11.0-changes.md
    ("2.1.11", "Requirement"): "<p>The EcoCommute system shall require a start place and a destination place and show on one screen, for walking, cycling and scooter (only those the Commuter has), driving, and the bus when the published timetable is installed, the route distance, travel time, estimated CO2e and estimated difference from the always-drive baseline, each based on that mode's own route.</p>",
    ("3.3.1.9", "Requirement"): "The EcoCommute system shall compare walking, cycling, scooter, driving and bus by distance, time, estimated CO2e and difference from the always-drive baseline.",
}


def redescribe(m, number, cls, text):
    e = m.find(number, cls)
    e.find("description").text = text


def unique_control_structure_ids(m):
    """Give every action its own simulation control-structure ids.

    Every action copied from UC.1.10 (the 10.9 UC.3 steps and the new ones) carries UC.1.10's two ids,
    so 23 actions shared them. Imported into a fresh Innoslate project, such files gave "prior action is
    dependent on the later action" on UC.3 and UC.4 (pure 10.9 included), while the same flows in UC.1,
    whose ids are unique, did not. The cause is inferred from that, not seen; the new ids are made from
    each entity's global id, so the same script always gives the same ids.
    """
    ids = Counter(
        x.get("id") for e in m.db.findall("entity") for x in e.iter()
        if x is not e and x.get("id") and "-" in x.get("id")
    )
    original = m.find("UC.1.10", "Action")
    for e in m.db.findall("entity"):
        if e is original:
            continue
        for x in e.iter():
            if x is not e and x.get("id") and "-" in x.get("id") and ids[x.get("id")] > 1:
                x.set("id", str(uuid.uuid5(uuid.NAMESPACE_URL, e.findtext("globalId") + x.get("id"))))


def write_timelines(m, parents=("UC.3", "UC.4")):
    """Write each parent action's sequence: START, its steps in number order, END.

    Innoslate checks "prior action is dependent on the later action" against the timeline held in the
    parent's simulation data. UC.1 and F.2 (drawn in Innoslate) have that chain; the UC.3 parent of 10.9
    and the new UC.4 had only START and END, so Innoslate guessed an order and flagged flows between steps
    (its Fix dialog: "time-traveling input/outputs are not permitted"). A second import of the same file
    happened to clear it. The chain follows the format of F.2's own simulation data.
    """
    for number in parents:
        parent = m.find(number, "Action")
        children = sorted(
            (e for e in m.db.findall("entity") if (e.findtext("number") or "").startswith(number + ".")
             and e.findtext("number").count(".") == number.count(".") + 1 and m.cls(e) == "Action"),
            key=lambda e: int(e.findtext("number").rsplit(".", 1)[1]),
        )
        sim = parent.find("simulationData")
        for old in sim.findall("controlStructure"):
            sim.remove(old)

        def new_id(tag):
            return str(uuid.uuid5(uuid.NAMESPACE_URL, parent.findtext("globalId") + tag))

        start = ET.SubElement(sim, "controlStructure", id=new_id("start"))
        ET.SubElement(start, "type").text = "START"
        tail = start
        for child in children:
            step = ET.SubElement(tail, "successorStructure", id=new_id(child.findtext("number")))
            ET.SubElement(step, "entityGlobalId").text = child.findtext("globalId")
            ET.SubElement(step, "type").text = "SERIAL"
            tail = step
        end = ET.SubElement(tail, "successorStructure", id=new_id("end"))
        ET.SubElement(end, "type").text = "END"


def build():
    m = base.Model(SRC)
    m.rng = random.Random(1100)  # fixed seed: the same script always gives the same ids
    t_need = m.find("1.1.4", "Statement")
    t_req_stk = m.find("2.1.4", "Requirement")
    t_req_sys = m.find("3.3.1.5", "Requirement")
    t_action = m.find("UC.1.10", "Action")
    t_asset = m.find("X.3", "Asset")
    t_io = m.find("IO.20", "Input/Output")
    t_conduit = m.find("", "Conduit", "Forecast")
    t_risk = m.find("TR.3", "Risk")
    label_commuter = m.find("2.1.4", "Requirement")
    label_sponsor = m.find("2.3.3", "Requirement")

    m.new["io_comparison"] = m.find("", "Input/Output", "Mode Comparison")  # from 10.9; m.new is only a lookup here

    for (number, cls), text in CHANGED.items():
        redescribe(m, number, cls, text)

    # ---- needs ----------------------------------------------------------------------------
    needs = [
        ("1.1.12", "Plan with the real bus schedule", "SH.1", "1.1",
         "I need bus options built from the real timetable for the day and time I leave, so I can see whether the bus is a real choice for this trip."),
        ("1.1.13", "Compare only what I have, and share rides fairly", "SH.1", "1.1",
         "I need the comparison to offer only the vehicles I have and to credit a shared car ride fairly, so the figures describe my real choices."),
        ("1.1.14", "Keep my trips between visits", "SH.1", "1.1",
         "I need my trips, vehicles and settings kept under my own account, so my progress is not lost when I leave and nobody else sees my trips."),
        ("1.3.5", "Keep the pilot to invited participants", "SH.3", "1.3",
         "I need the pilot to be open only to the people we invite, so the pilot data comes from the intended cohort and a small free service is not used up by strangers."),
    ]
    for number, name, stakeholder, parent, text in needs:
        m.add(number, t_need, number, name, f"<p>{text}</p>")
        m.link(number, "decomposes", m.find(parent, "Statement"))
        m.link(number, "traced to", m.find(stakeholder, "Asset"))

    # ---- stakeholder requirements -----------------------------------------------------------
    def stk_rationale(rationale, moe, why, validation, method, needs_):
        return (f"Rationale: {rationale}\nMOE: {moe}\nMOE selection: {why}\nValidation: {validation}\n"
                f"Verification method: {method}\nSource needs: {needs_} (proposed in model 11.0)")

    stakeholder_reqs = [
        ("2.1.15", "plan a bus ride from the published timetable", "2.1", label_commuter, ("1.1.12",),
         "The EcoCommute system shall show, for the date and time the Commuter leaves, the direct bus ride of each route that links the two places, with the route, the boarding and alighting stops, the departure and arrival times and the door-to-door time taken from the published timetable, or the reason no bus is offered.",
         stk_rationale("A typed bus time is not data; the transit agency publishes its timetable, so the bus can be compared on the same footing as the other ways. Only direct rides are planned, and the page says the timetable is not live.",
                       "Offered rides that do not exist in the published timetable for the chosen date and time, in a reference set of trips (target 0)",
                       "A ride that is not in the timetable would mislead the Commuter, and the count is exact.",
                       "Pick reference trips and times (weekday, weekend, after midnight, a date with no service); compare the offered rides with the timetable; check that every missing bus has a stated reason.",
                       "Test", "1.1.12"),
         ("UC.3.13", "UC.3.15")),
        ("2.1.16", "offer only the vehicles the Commuter has and share a car's emissions", "2.1", label_commuter, ("1.1.13",),
         "The EcoCommute system shall offer cycling and scooter only when the Commuter says they have one, and shall divide the estimated emissions of a shared car trip equally among the 2 to 8 people the Commuter enters.",
         stk_rationale("The comparison is only useful if every way shown is one the Commuter can take, and a shared ride emits less per person. The default of no vehicle and the range of 2 to 8 people are project assumptions to confirm.",
                       "Ways offered that the Commuter did not say they have, and shared-trip figures that differ from the equal share (target 0 for both)",
                       "Both are exact counts on a seeded set.",
                       "Run seeded plans with and without each vehicle and with 1 to 9 people; compare the offered ways and the per-person figures with the expected ones.",
                       "Test", "1.1.13"),
         ("UC.3.12", "UC.3.5", "UC.3.8")),
        ("2.1.17", "keep trips under the Commuter's own account", "2.1", label_commuter, ("1.1.14",),
         "The EcoCommute system shall keep each Commuter's confirmed trips, vehicles and preferences under that Commuter's account between visits, shall show no Commuter another account's trips, and shall let the Commuter download or delete the account's data.",
         stk_rationale("Progress and badges mean something only if they survive a restart, and the trips are personal data. This extends 2.1.7 (restrict access) and 2.1.8 (delete on request) to the stored account.",
                       "Trips lost across a restart, shown to another account, or left after account deletion in a seeded two-account test (target 0 for all three)",
                       "Each is an exact, observable failure.",
                       "Create two accounts, save trips, restart the service, compare what each sees; download and delete one account and inspect the stored data.",
                       "Test", "1.1.14"),
         ("UC.4", "UC.4.1", "UC.4.4", "UC.4.5")),
        ("2.1.18", "show matching place suggestions while typing", "2.1", label_commuter, ("1.1.1", "1.1.9"),
         "The EcoCommute system shall show matching place suggestions, each with its name and area, while the Commuter types a start or destination place, and shall not require the Commuter to type the whole name.",
         stk_rationale("Typing complete addresses slows entry (2.1.1) and misspelled places give no route; suggestions find known places without a full name. The 90% target is a proposal.",
                       "Percentage of searches for known campus places in which the intended place appears among the suggestions after the first four characters (proposed target 90% or more)",
                       "It measures whether the aid finds the place.",
                       "A list of 20 known campus places typed by testers; count how often the intended place is suggested.",
                       "Test", "1.1.1, 1.1.9"),
         ("UC.3.14",)),
        ("2.3.8", "create accounts only for invited participants", "2.3", label_sponsor, ("1.3.5",),
         "The EcoCommute system shall create an account only for a person who presents a valid invite code.",
         stk_rationale("The pilot cohort is invited, and the free place and route services have small quotas. The number of codes, who holds them and whether codes expire are project choices to confirm with the sponsor.",
                       "Accounts created with a wrong, missing or revoked invite code (target 0)",
                       "An exact count over deliberate bad attempts.",
                       "Attempt sign-up with no code, a wrong code and a revoked code; confirm that no account exists afterwards.",
                       "Test", "1.3.5"),
         ("UC.4", "UC.4.2", "UC.4.3")),
    ]
    for number, name, parent, label, needs_, text, rationale, satisfied_by in stakeholder_reqs:
        m.add(number, t_req_stk, number, name, f"<p>{text}</p>",
              {"Rationale": rationale, "Status": "Draft", **{q: "false" for q in QUALITY}}, label_from=label)
        m.link(number, "decomposes", m.find(parent, "Requirement"))
        for need in needs_:
            m.link(need, "traced to", number)
    stk_satisfied = {r[0]: r[-1] for r in stakeholder_reqs}

    # ---- external system, conduit and input/outputs -------------------------------------------
    m.add("X.7", t_asset, "X.7", "Transit Schedule Publisher", "The transit agency that publishes its timetable as a GTFS file (Tompkins Consolidated Area Transit).")
    m.link("X.7", "decomposes", m.find("0", "Asset"))

    def io(key, name, description):
        m.add(key, t_io, "", name, description)

    io("io_schedule", "Bus Schedule", "The published timetable: routes, stops, route shapes, trips and the days each service runs.")
    io("io_trip_options", "Trip Options", "The date and time of leaving, the vehicles the Commuter has, and for a car trip the number of people sharing it.")
    io("io_suggestions", "Place Suggestions", "Matching places, with name and area, for the text typed so far.")
    io("io_account_details", "Account Details", "User name, password and, when signing up, the invite code.")
    io("io_session", "Signed-in Session", "The signed token that tells the service which account a later request belongs to.")
    m.add("cd_schedule", t_conduit, "", "Transit schedule", "")
    m.link("cd_schedule", "transfers", "io_schedule")
    m.link("cd_schedule", "connects to", "X.7")
    m.link("cd_schedule", "connects to", m.find("C.0", "Asset"))

    # ---- UC.3 additions (the numbers continue UC.3.1-UC.3.11 of model 10.9) ------------------
    web_steps = [
        # Flows only join neighbouring steps, as in UC.3.1-UC.3.11: the first import of 11.0 gave
        # "prior action is dependent on the later action" for UC.3 and UC.4 when steps were skipped.
        # The schedule reaches UC.3.13 through the Transit schedule conduit, not through a step flow.
        ("UC.3.12", "Select Vehicles and Ride Sharing", ("X.1",), (), ("io_trip_options",)),
        ("UC.3.13", "Plan Bus Ride", ("C.2",), ("io_trip_options",), ()),
        ("UC.3.14", "Suggest Places", ("C.3",), (), ("io_suggestions",)),
        ("UC.3.15", "Publish Bus Schedule", ("X.7",), (), ("io_schedule",)),
    ]
    for number, name, performers, receives, generates in web_steps:
        m.add(number, t_action, number, name, "")
        m.link(number, "decomposes", "UC.3")
        for p in performers:
            m.link(m.find(p, "Asset"), "performs", number)
        for r in receives:
            m.link(number, "receives", r)
        for g in generates:
            m.link(number, "generates", g)

    # ---- UC.4 Sign Up and Log In ------------------------------------------------------------------
    m.add("UC.4", t_action, "UC.4", "Sign Up and Log In", "Create an account with an invite code, or log in, so that trips are kept under the Commuter's own account.")
    m.link("UC.4", "decomposes", m.find("UC.0", "Action"))
    m.link("X.1", "performs", "UC.4")
    uc4 = [
        ("UC.4.1", "Open Log-in Page", ("X.1",), (), ()),
        ("UC.4.2", "Enter Account Details", ("X.1",), (), ("io_account_details",)),
        ("UC.4.3", "Verify Invite Code and Credentials", ("C.2",), ("io_account_details",), ("io_session",)),
        ("UC.4.4", "Store Account and Trips", ("C.3",), ("io_session",), ()),
        ("UC.4.5", "Present Signed-in Pages", ("C.1",), (), ()),
    ]
    for number, name, performers, receives, generates in uc4:
        m.add(number, t_action, number, name, "")
        m.link(number, "decomposes", "UC.4")
        for p in performers:
            m.link(m.find(p, "Asset"), "performs", number)
        for r in receives:
            m.link(number, "receives", r)
        for g in generates:
            m.link(number, "generates", g)
    for req, actions in stk_satisfied.items():
        for a in actions:
            m.link(a, "satisfies", req)

    # ---- system requirements ------------------------------------------------------------------------
    def sys_rationale(rationale, mop, criteria, method, stakeholder):
        return (f"Rationale: {rationale}\nMOP: {mop}\nVerification criteria: {criteria} Method: {method}.\n"
                f"Stakeholder requirements: {stakeholder}\nStatus note: proposed in model 11.0.")

    F2 = "F.2"
    sys_reqs = [
        ("3.1.1.11", "accept the date and time of leaving", "3.1.1", ("2.1.15",), ("io_trip_options", F2),
         "The EcoCommute system shall accept the date and time at which the Commuter leaves.",
         sys_rationale("Which buses run depends on the day and the hour.", "Plans made with no leaving time and no default (target 0).", "Submit with a time, with none and with an impossible date.", "Test", "2.1.15")),
        ("3.1.1.12", "accept the vehicles the Commuter has", "3.1.1", ("2.1.16",), ("io_trip_options", F2),
         "The EcoCommute system shall accept which vehicles, a bike or a scooter, the Commuter has.",
         sys_rationale("Only the Commuter knows what they own.", "Vehicle values accepted outside the allowed list (target 0).", "Submit allowed and unknown values.", "Test", "2.1.16")),
        ("3.1.1.13", "accept the number of people sharing a car", "3.1.1", ("2.1.16",), ("io_trip_options", F2),
         "The EcoCommute system shall accept the number of people sharing a car trip, from 2 to 8.",
         sys_rationale("The share of emissions depends on the number of occupants, which only the Commuter knows.", "Counts accepted outside 2 to 8 for a shared trip (target 0).", "Submit 0, 1, 2, 8, 9 and text.", "Test", "2.1.16")),
        ("3.1.1.14", "accept an invite code and log-in credentials", "3.1.1", ("2.3.8", "2.1.17"), ("io_account_details", "io_session", F2),
         "The EcoCommute system shall accept a user name, a password and, when an account is created, an invite code.",
         sys_rationale("These are what identify a person and admit an invited one.", "Accounts created or sessions opened without the required fields (target 0).", "Submit each field missing in turn.", "Test", "2.3.8, 2.1.17")),
        ("3.1.2.8", "provide place suggestions to the Commuter", "3.1.2", ("2.1.18",), ("io_suggestions", F2),
         "The EcoCommute system shall provide the Commuter with up to five matching places, each with a name and an area, for the text typed so far.",
         sys_rationale("Suggestions replace typing a full address.", "Suggestion lists longer than five or without an area (target 0).", "Type reference fragments; inspect the lists.", "Test", "2.1.18")),
        ("3.1.2.9", "provide bus rides and the reason for no bus to the Commuter", "3.1.2", ("2.1.15",), ("io_comparison", F2),
         "The EcoCommute system shall provide the Commuter with each direct bus ride found, or the reason no bus is offered.",
         sys_rationale("A silent absence of the bus would look like a bug.", "Plans with neither a ride nor a reason (target 0).", "Plan trips with and without a bus and compare.", "Test", "2.1.15")),
        ("3.2.11", "utilize published timetable file ingestion to interface with the Transit Schedule Publisher", "3.2", ("2.1.15",), ("X.7", "C.0", "cd_schedule", "io_schedule", F2),
         "The EcoCommute system shall utilize a published timetable file ingestion to interface with the Transit Schedule Publisher.",
         sys_rationale("The agency publishes a file rather than a service; reading it on demand keeps the app independent of the agency's servers while planning.", "Plans that call the agency while the Commuter waits (target 0).", "Inspect the planning path and run it offline.", "Inspection and Test", "2.1.15")),
        ("3.3.1.13", "plan direct bus rides", "3.3.1", ("2.1.15",), ("F.2.5",),
         "The EcoCommute system shall plan, from the published timetable, the direct ride of each bus route that links the two places on the chosen date and time, and shall give the reason when none does.",
         sys_rationale("Direct rides can be checked against the timetable; transfers are outside the pilot.", "Rides offered that are not in the timetable (target 0).", "Reference trips and times compared with the timetable.", "Test", "2.1.15")),
        ("3.3.1.14", "share a car trip's emissions among its occupants", "3.3.1", ("2.1.16",), ("F.2.3",),
         "The EcoCommute system shall divide the estimated emissions of a shared car trip equally among its occupants and shall record the trip with the number of people.",
         sys_rationale("A shared ride emits less per person than driving alone.", "Per-person figures that differ from the equal share (target 0).", "Seeded plans with 1 to 8 people.", "Test", "2.1.16")),
        ("3.3.1.15", "manage accounts and invite codes", "3.3.1", ("2.3.8", "2.1.17"), ("F.2.4",),
         "The EcoCommute system shall create an account only when the invite code is valid, shall open a session only after a correct password, and shall let an account be downloaded or deleted.",
         sys_rationale("Accounts hold the trips and gate the free services.", "Accounts created or sessions opened against these conditions (target 0).", "Deliberate bad attempts and a delete-and-inspect test.", "Test", "2.3.8, 2.1.17")),
        ("3.3.1.16", "keep trips per account", "3.3.1", ("2.1.17",), ("F.2.4",),
         "The EcoCommute system shall store each confirmed trip, the vehicles and the preferences under the signed-in account and keep them across restarts.",
         sys_rationale("Progress must survive a restart and stay with its owner.", "Trips missing after a restart or visible to another account (target 0).", "Two accounts, a restart, and a comparison.", "Test", "2.1.17")),
        ("3.3.1.17", "suggest places and remember answers", "3.3.1", ("2.1.18",), ("F.2.2",),
         "The EcoCommute system shall suggest matching places while the Commuter types and shall reuse places and routes it already looked up.",
         sys_rationale("Reusing answers keeps the free place service within its quota.", "Repeated identical questions sent to the service (target 0).", "Ask twice and inspect the outbound requests.", "Test", "2.1.18")),
        ("3.4.5.5", "store passwords and invite codes only as one-way hashes", "3.4.5", ("2.3.8", "2.1.7"), (F2,),
         "The EcoCommute system shall store passwords and invite codes only as salted one-way hashes.",
         sys_rationale("A copy of the database must not reveal passwords or codes.", "Stored values that can be read back as the original (target 0).", "Inspect the stored fields.", "Inspection", "2.3.8, 2.1.7")),
        ("3.4.5.6", "lock log-in after repeated wrong passwords", "3.4.5", ("2.3.8", "2.1.7"), (F2,),
         "The EcoCommute system shall refuse log-in for the rest of a 15-minute window after 5 wrong passwords for one user name.",
         sys_rationale("The lockout slows password guessing. The count and window are project assumptions for a small invited group.", "Log-ins accepted during a lockout (target 0).", "Make 5 wrong attempts, then a correct one.", "Test", "2.3.8, 2.1.7")),
        ("3.4.5.7", "keep no record of who asked in the place and route cache", "3.4.5", ("2.5.1", "2.1.7"), (F2,),
         "The EcoCommute system shall keep cached place and route answers without any record of which account asked, and shall not cache routes that start or end at the Commuter's own position.",
         sys_rationale("A shared cache must not become a location history.", "Cache entries that hold an account or a personal position (target 0).", "Inspect the cache after a seeded session.", "Inspection", "2.5.1, 2.1.7")),
        ("3.4.6.3", "state that bus times come from a timetable", "3.4.6", ("2.1.15", "2.4.4"), (F2,),
         "The EcoCommute system shall state next to each bus ride that the times come from the published timetable and are not live.",
         sys_rationale("A late or cancelled bus is not known.", "Bus rides shown without the statement (target 0).", "Inspect the bus card.", "Inspection", "2.1.15, 2.4.4")),
    ]
    for number, name, parent, traced_from, satisfied_by, text, rationale in sys_reqs:
        m.add(number, t_req_sys, number, name, text, {"Rationale": rationale, "Status": "Draft", **{q: "false" for q in QUALITY}})
        m.link(number, "decomposes", m.find(parent, "Requirement"))
        for s in traced_from:
            m.link(m.ref(s), "traced to", number)
        for sat in satisfied_by:
            m.link(sat, "satisfies", number)

    # ---- risks ------------------------------------------------------------------------------------------
    risks = [
        ("TR.13", "Timetable terms of use unknown and the feed expires",
         "No licence or terms for redistributing the transit agency's timetable file were found, and the current file ends on 2026-12-19. Mitigation: keep the file out of the repository, refresh it with the update command when the agency publishes a new one, and ask the agency about terms before any public use.",
         ("3.2.11", "3.3.1.13", "3.4.6.3")),
        ("TR.14", "The account database holds personal data on one computer",
         "Accounts, trips with places and the cache sit in one file on the owner's computer; a lost disk or a copied file exposes them, and whether the course allows real people's trips is unconfirmed. Mitigation: keep the file private and backed up, delete accounts on request, and ask the course staff before collecting real trips.",
         ("3.3.1.15", "3.3.1.16", "3.4.5.5")),
        ("TR.15", "Shared invite codes and plain http on a shared network",
         "Three shared invite codes admit many accounts, and plain http crosses a shared network unencrypted, so a code or password could be read or passed on. Mitigation: use a private network or a tunnel with https, revoke and replace a code that leaks, and keep the lockout.",
         ("2.3.8", "3.4.5.5", "3.4.5.6")),
    ]
    for number, name, text, related in risks:
        m.add(number, t_risk, number, name, text,
              {"Status": "Open", "Probability": 0.5, "Consequence": 0.5, "Consequence Description": text.split(" Mitigation:")[0]})
        for req in related:
            m.link(m.find(req, "Requirement"), "relates", number)
    unique_control_structure_ids(m)
    write_timelines(m)
    return m


def main():
    m = build()
    m.root.set("createdDateTime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ET.indent(m.tree, space="    ")
    m.tree.write(OUT, encoding="utf-8", xml_declaration=False)
    with open(OUT, "r", encoding="utf-8") as f:
        body = f.read()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body)
    print(f"wrote {OUT}: {len(m.new)} new entities")


if __name__ == "__main__":
    sys.exit(main())
