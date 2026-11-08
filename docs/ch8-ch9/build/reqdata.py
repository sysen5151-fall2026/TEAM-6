"""Requirement data for the Chapter 8 + 9 report and the model patch (EcoCommute 11.3).

Document 4: System Design Output Requirements (one requirement per leaf first-level
function, stated against its subsystem).
Document 5: Reference Data Subsystem Component Specification (input, output, interface,
functional and system-wide requirements for C.0.2).
Each record: num, name, stmt, parents (system or design-output requirements), stk
(stakeholder requirements), rat, mop, ver, method, asset (satisfying asset), func
(satisfying function), kind, [flow = flow-down method].
"""
from collections import OrderedDict

DOC4 = ("4", "System Design Output Requirements",
        "Design output requirements for the leaf first-level functions, each stated against the subsystem that performs it. "
        "Derived from the system functional requirements (3.3.1.x).")
DOC4_HDR = [("4.1", "Subsystem Functional Requirements",
             "Requirements for what each first-level subsystem performs, one per leaf first-level function.")]

DOC5 = ("5", "Reference Data Subsystem Component Specification",
        "Component requirements for C.0.2 Reference Data Subsystem, derived from the second-level IDEF0 of F.2.2 and from the "
        "system requirements; kept apart from the system requirements document.")
DOC5_HDR = [
    ("5.1", "Input Requirements", "Requirements for what the Reference Data Subsystem accepts."),
    ("5.2", "Output Requirements", "Requirements for what the Reference Data Subsystem provides."),
    ("5.3", "Interface Requirements", "Requirements for the conduits that cross the subsystem boundary."),
    ("5.4", "Functional Requirements", "One requirement for each second-level function F.2.2.1 to F.2.2.4."),
    ("5.5", "System-wide Requirements", "System-wide requirements flowed down to the subsystem, with the flow-down method."),
]


def R(num, name, stmt, parents, stk, rat, mop, ver, method, asset, func=None, flow=None):
    return dict(num=num, name=name, stmt=stmt, parents=parents, stk=stk, rat=rat, mop=mop, ver=ver,
                method=method, asset=asset, func=func, flow=flow)


# ------------------------------------------------------------------ Document 4: leaf first-level functions
SDOR = [
    R("4.1.1", "operate service",
      "The Operations Subsystem shall operate the pilot service by deploying releases to the Hosting Provider, monitoring availability and running retirement.",
      ["3.3.1.8"], ["2.2.4", "2.3.3", "2.3.6", "2.3.7"],
      "A service that stays up and can be retired cleanly is a pilot condition (needs 1.2.3 and 1.3.4); one asset owns release, monitoring and retirement so accountability is not shared.",
      "Share of one-minute availability checks passed in a month (target 99.5% or more); identifiable records left after a retirement rehearsal (target 0).",
      "Review the monthly monitoring report; run a retirement rehearsal on a copy of the pilot data.", "Analysis", "C.0.0", "F.2.0"),
    R("4.1.2", "collect commute entries",
      "The Entry Subsystem shall collect commute entries through a responsive web entry form, validating each entry and checking recorded consent before the entry is passed on.",
      ["3.3.1.1"], ["2.1.1", "2.1.8", "2.1.9", "2.5.2"],
      "Entry effort is the main barrier to repeated logging; invalid or unconsented entries must stop at the boundary so no other subsystem handles them.",
      "Share of timed entry tasks completed in 30 seconds or less (target 80% or more); invalid or unconsented entries passed on (target 0).",
      "Pilot usability session with at least 20 participants logging five trips each; rule test set of invalid and unconsented entries.", "Test", "C.0.1", "F.2.1"),
    R("4.1.3", "estimate commute emissions",
      "The Estimation Subsystem shall estimate the CO2e of each validated trip from the applicable emission factor and the trip distance, and its difference from the always-drive baseline.",
      ["3.3.1.3"], ["2.1.2", "2.1.3", "2.4.3"],
      "The estimate is the core product value; giving the factor source, version and distance convention with each result lets reviewers trace every number (need 1.4.1).",
      "Difference between computed and hand-calculated CO2e for the agreed reference cases (target 0 g after rounding to the nearest gram); share of results carrying source, version and distance convention (target 100%).",
      "Run the reference-case set against the Estimation Subsystem; inspect a sample of 50 results.", "Test", "C.0.3", "F.2.3"),
    R("4.1.4", "manage commute records",
      "The Records Subsystem shall store each accepted trip record, update weekly and monthly trends, restrict access to the owning Commuter and delete records on request and at retirement.",
      ["3.3.1.4"], ["2.1.6", "2.1.7", "2.1.8", "2.3.2", "2.3.6"],
      "Trip records are personal data; keeping storage, trends and deletion in one asset gives one place to enforce consent, access and deletion (needs 1.1.6 and 1.3.4).",
      "Trip records exposed to any other role in access tests (target 0); deletion requests that leave an identifiable record (target 0); accepted entries without exactly one timestamped event (target 0).",
      "Role-based access test matrix; deletion test on test accounts including backups in scope; reconcile the event log with accepted entries.", "Test", "C.0.4", "F.2.4"),
    R("4.1.5", "evaluate feasible alternatives",
      "The Recommendation Subsystem shall select one feasible lower-emission alternative, with a stated reason, from the trip distance, the forecast weather and the Commuter's feasibility settings.",
      ["3.3.1.5"], ["2.1.4", "2.1.5"],
      "Advice changes behaviour only if it fits the Commuter's situation; explicit rules can be inspected and explained (need 1.1.4).",
      "Recommendations that include a mode marked not feasible (target 0); share of eligible trips with one alternative and a reason (target 100%).",
      "Rule test set covering every combination of excluded modes and weather states.", "Test", "C.0.5", "F.2.5"),
    R("4.1.6", "present commute results",
      "The Presentation Subsystem shall present each trip result, with trend, baseline difference, method disclosure, alternative and a plain-language explanation that restates only calculated facts, in a responsive result view.",
      ["3.3.1.6"], ["2.1.2", "2.1.3", "2.1.6", "2.1.9", "2.1.10"],
      "The result view is where the Commuter meets the model output; the explanation may not calculate or invent (need 1.1.8, risk R8).",
      "Time from entry submission to result display (threshold 3 seconds); sampled explanations with a figure, condition or mode not in the calculated result (target 0); unresolved WCAG 2.2 Level AA failures (target 0).",
      "Timing test on three reference devices; inspect 50 explanations field by field against the calculated result; accessibility audit of the result view.", "Test", "C.0.6", "F.2.6"),
    R("4.1.7", "summarize pilot results",
      "The Reporting Subsystem shall provide an authorized Pilot Administrator with approved aggregate summaries that exclude individual identifiers and suppress any group of fewer than 5 Commuters.",
      ["3.3.1.7"], ["2.2.1", "2.2.2", "2.2.3", "2.3.4", "2.3.7"],
      "Institutional evidence must not re-identify anyone; suppression and exclusion are applied where the aggregate is made, not downstream (need 1.2.2).",
      "Reported groups with fewer than 5 Commuters (target 0); individual identifiers or trip records in outputs (target 0); measures of effectiveness reported before December 18, 2026 (target all defined).",
      "Aggregation test with seeded groups of size 1 to 10; output inspection; evaluation report checked against the measure list at the launch-decision gate.", "Test", "C.0.7", "F.2.7"),
]

# ------------------------------------------------------------------ Document 5: component specification
INPUT = [
    R("5.1.1", "accept validated commute entry",
      "The Reference Data Subsystem shall accept validated commute entries from the Entry Subsystem.",
      ["3.3.1.2", "4.1.2"], ["2.4.1", "2.1.4"],
      "The factor and the forecast are chosen per trip, so the subsystem needs the mode, geography, coarse area and trip time of every accepted entry.",
      "Share of validated entries accepted without loss of mode, geography, coarse area or trip time (target 100%).",
      "Replay a set of validated entries and compare the fields received with the fields sent.", "Test", "C.0.2", "F.2.2"),
    R("5.1.2", "accept weather forecast data",
      "The Reference Data Subsystem shall accept weather forecast data, with a forecast timestamp, from Open-Meteo.",
      ["3.1.1.3"], ["2.1.4"],
      "The recommendation rule needs forecast weather and the time the forecast was made so that a stale forecast can be recognised.",
      "Share of well-formed forecast responses accepted (target 100%); malformed responses that stop the subsystem (target 0).",
      "Feed fixtures of valid, empty and malformed Open-Meteo responses through the Weather Client interface.", "Test", "C.0.2", "F.2.2"),
    R("5.1.3", "accept reviewed emission factors",
      "The Reference Data Subsystem shall accept reviewed emission factors, with source, units, geography, methodology and version, from the Emission Factor Publisher.",
      ["3.1.1.4"], ["2.4.1"],
      "Only reviewed, versioned factors may govern an estimate; the five attributes are what the disclosure to the Commuter is built from.",
      "Share of accepted factor sets that carry all five attributes (target 100%); sets accepted with a missing attribute (target 0).",
      "Load a valid factor file and files each missing one attribute; inspect the store.", "Test", "C.0.2", "F.2.2"),
]
OUTPUT = [
    R("5.2.1", "provide weather request",
      "The Reference Data Subsystem shall provide weather requests, containing only a coarse location and the trip time, to Open-Meteo.",
      ["3.1.2.2"], ["2.5.1", "2.1.4"],
      "Open-Meteo is a third party; nothing finer than a coarse area may leave the system (need 1.5.1).",
      "Share of outgoing weather requests that contain only a coarse area and a trip time (target 100%).",
      "Capture every request sent in a test run and inspect its fields.", "Inspection", "C.0.2", "F.2.2"),
    R("5.2.2", "provide emission factor record",
      "The Reference Data Subsystem shall provide the applicable emission factor record, with source, units, geography and version, to the Estimation Subsystem.",
      ["3.3.1.2", "4.1.3"], ["2.4.1", "2.1.3"],
      "The Estimation Subsystem must show where each number comes from, so the provenance travels with the factor.",
      "Share of emission factor records provided with source, units, geography and version (target 100%).",
      "Inspect the records returned for a sample of 50 reference entries.", "Inspection", "C.0.2", "F.2.2"),
    R("5.2.3", "provide trip weather forecast",
      "The Reference Data Subsystem shall provide the trip weather forecast, with its forecast timestamp or a forecast-unavailable flag, to the Recommendation Subsystem.",
      ["3.3.1.2", "4.1.5"], ["2.1.4"],
      "The recommendation rule must know whether it can rely on the forecast; an explicit flag avoids silent assumptions.",
      "Share of trip forecasts provided with a timestamp or an unavailable flag (target 100%).",
      "Run entries with a live stub, a late stub and no response; inspect each output.", "Test", "C.0.2", "F.2.2"),
]
INTERFACE = [
    R("5.3.1", "interface with Open-Meteo through the weather query",
      "The Reference Data Subsystem shall interface with Open-Meteo through the Weather query conduit using an HTTPS API request.",
      ["3.2.3"], ["2.1.4"],
      "Carries the external interface requirement 3.2.3 down to the subsystem that owns the call.",
      "Share of weather queries sent over HTTPS to the documented endpoint (target 100%).",
      "Inspect the client configuration and the traffic of a test run.", "Inspection", "C.0.2", "F.2.2"),
    R("5.3.2", "interface with Open-Meteo through the forecast",
      "The Reference Data Subsystem shall interface with Open-Meteo through the Forecast conduit using a structured HTTPS API response.",
      ["3.2.4"], ["2.1.4"],
      "Carries the external interface requirement 3.2.4 down; a structured response can be validated against a schema.",
      "Share of responses validated against the response schema before use (target 100%).",
      "Feed schema-conforming and non-conforming responses; confirm only the former are used.", "Test", "C.0.2", "F.2.2"),
    R("5.3.3", "interface with the Emission Factor Publisher through reviewed factors",
      "The Reference Data Subsystem shall interface with the Emission Factor Publisher through the Reviewed factors conduit using reviewed file or source-document ingestion.",
      ["3.2.5"], ["2.4.1"],
      "Carries the external interface requirement 3.2.5 down; factors come from a reviewed file, not a live call.",
      "Share of factor sets loaded from a reviewed file or source document (target 100%).",
      "Inspect the load log of the pilot build for the source of every factor set.", "Inspection", "C.0.2", "F.2.2"),
    R("5.3.4", "interface with the Entry Subsystem",
      "The Reference Data Subsystem shall interface with the Entry Subsystem through the Entry to reference data conduit using an internal service API.",
      ["3.3.1.2", "4.1.2"], ["2.4.1"],
      "Internal conduit K.12 of the first-level asset diagram; it carries IO.12 Validated Commute Entry.",
      "Share of calls on the conduit that follow the interface definition (target 100%).",
      "Contract test of the internal service API.", "Test", "C.0.2", "F.2.2"),
    R("5.3.5", "interface with the Estimation Subsystem",
      "The Reference Data Subsystem shall interface with the Estimation Subsystem through the Factor record conduit using an internal service API.",
      ["3.3.1.2", "4.1.3"], ["2.4.1"],
      "Internal conduit K.16; it carries IO.14 Emission Factor Record.",
      "Share of calls on the conduit that follow the interface definition (target 100%).",
      "Contract test of the internal service API.", "Test", "C.0.2", "F.2.2"),
    R("5.3.6", "interface with the Recommendation Subsystem",
      "The Reference Data Subsystem shall interface with the Recommendation Subsystem through the Trip forecast conduit using an internal service API.",
      ["3.3.1.2", "4.1.5"], ["2.1.4"],
      "Internal conduit K.17; it carries IO.15 Trip Weather Forecast.",
      "Share of calls on the conduit that follow the interface definition (target 100%).",
      "Contract test of the internal service API.", "Test", "C.0.2", "F.2.2"),
    R("5.3.7", "interface with the Route Service through the route request",
      "The Reference Data Subsystem shall interface with the Route Service through the Route request conduit using an HTTPS request.",
      ["3.2.9"], ["2.1.18"],
      "Added by model 11.0: place suggestion and place resolution (system requirement 3.3.1.17) are allocated to F.2.2 and call the Route Service. This interaction is not yet in the second-level IDEF0, which gets a fifth function in the next iteration.",
      "Share of Route Service calls sent over HTTPS to the documented endpoint (target 100%).",
      "Inspect the route adapter configuration and the traffic of a test run.", "Inspection", "C.0.2", "F.2.2"),
    R("5.3.8", "interface with the Route Service through the route response",
      "The Reference Data Subsystem shall interface with the Route Service through the Route response conduit using a structured HTTPS response.",
      ["3.2.10"], ["2.1.18"],
      "Added by model 11.0: carries the external interface requirement 3.2.10 down; a structured response can be validated before use and replaced by a labelled fallback when it is malformed.",
      "Share of Route Service responses validated before use (target 100%); malformed responses that stop the subsystem (target 0).",
      "Feed conforming, malformed and missing responses through the route adapter.", "Test", "C.0.2", "F.2.2"),
]
FUNCTIONAL = [
    R("5.4.1", "load emission factors",
      "The Reference Data Subsystem shall load each reviewed emission factor set into a versioned factor set and reject any set that lacks source, units, geography, methodology or version.",
      ["3.3.1.2"], ["2.4.1"],
      "Unreviewed or unversioned factors would let an estimate that cannot be traced reach a Commuter (risk TR.1).",
      "Share of factor sets in the store that carry all five attributes (target 100%); incomplete sets that enter the store (target 0).",
      "Load valid and incomplete files; inspect the store and the rejection log.", "Test", "C.0.2.1", "F.2.2.1"),
    R("5.4.2", "select emission factor",
      "The Reference Data Subsystem shall select the applicable emission factor for each validated commute entry from the versioned factor set and return it with its provenance.",
      ["3.3.1.2"], ["2.4.1", "2.1.3"],
      "The factor depends on the travel mode and the geography; the Commuter must see which version produced the number.",
      "Share of reference entries for which the expected factor and version are returned (target 100%); selection time (threshold 0.2 seconds).",
      "Run a reference table of mode and geography combinations and compare with the expected factor.", "Test", "C.0.2.2", "F.2.2.2"),
    R("5.4.3", "request weather forecast",
      "The Reference Data Subsystem shall request a weather forecast from Open-Meteo for the coarse location and the time of each validated commute entry.",
      ["3.3.1.2"], ["2.1.4", "2.5.1"],
      "The recommendation rule depends on forecast weather; the request is built here so that the privacy limit is enforced in one place.",
      "Share of validated entries for which a request is sent (target 100%); requests carrying data finer than coarse area and time (target 0).",
      "Capture requests during a run of reference entries.", "Test", "C.0.2.3", "F.2.2.3"),
    R("5.4.4", "resolve trip forecast",
      "The Reference Data Subsystem shall resolve the forecast returned by Open-Meteo to the forecast for the trip location and time, with its forecast timestamp, or flag the forecast unavailable when no response arrives within 1.0 second.",
      ["3.3.1.2"], ["2.1.4"],
      "A response covers many hours and places; the trip needs one. A missing forecast must not stop the estimate.",
      "Share of fixtures resolved to the expected forecast hour (target 100%); runs where a missing response blocks the estimate (target 0).",
      "Fixture responses with several hours and places, a late response and no response.", "Test", "C.0.2.4", "F.2.2.4"),
]
SYSWIDE = [
    R("5.5.1", "cost no more than $90,000",
      "The Reference Data Subsystem shall cost no more than $90,000 to develop and deploy.",
      ["3.4.1.1"], ["2.3.1"],
      "Apportionment of the $750,000 system budget: 12% to this subsystem (budget in the cost apportionment table of Section 3.2.2). The share reflects two external interfaces and a versioned store; a detailed estimate is deferred to the design stage.",
      "Cost variance against $90,000 (target 0% or less).",
      "Subsystem cost forecast reviewed at each stage gate.", "Analysis", "C.0.2", "F.2.2", "Apportionment"),
    R("5.5.2", "be ready for integration by November 13, 2026",
      "The Reference Data Subsystem shall pass its verification tests and be ready for system integration no later than November 13, 2026.",
      ["3.4.1.2"], ["2.3.4"],
      "Apportionment of the schedule: results are due December 18, 2026 and the pilot needs four weeks of use, so the pilot must start by November 16, 2026 and the subsystems must be integrated before that (milestone table in Section 3.2.2). The Estimation Subsystem depends on the factor store, so this subsystem verifies first, two days before the other subsystems. The web application is already implemented, so the remaining work is verification and integration.",
      "Date on which all subsystem verification tests pass (threshold November 13, 2026 for integration; November 10, 2026 for this subsystem).",
      "Schedule review at the integration gate.", "Analysis", "C.0.2", "F.2.2", "Apportionment"),
    R("5.5.3", "return reference data within 1.2 seconds",
      "The Reference Data Subsystem shall return the emission factor record and the trip weather forecast within 1.2 seconds of receiving a validated commute entry, using no more than 1.0 second for the Open-Meteo call.",
      ["3.4.2.1"], ["2.1.2"],
      "Apportionment of the 3-second result time across the path (budget in the response-time table of Section 3.2.2). The external call dominates this subsystem's share, so the call is capped at 1.0 second and the rest at 0.2 second.",
      "95th percentile time from receipt of the entry to both outputs (threshold 1.2 seconds).",
      "Timing test with an Open-Meteo stub at 1.0 second latency and with the live service on three reference devices.", "Test", "C.0.2", "F.2.2", "Apportionment"),
    R("5.5.4", "maintain availability of at least 99.95 percent",
      "The Reference Data Subsystem shall maintain an availability of at least 99.95 percent during each month of the pilot, excluding Open-Meteo outages.",
      ["3.4.3.1"], ["2.2.4"],
      "Apportionment of the 0.5% monthly unavailability allowed by the system requirement (budget in the availability table of Section 3.2.2): 0.05% to this subsystem. Open-Meteo outages are outside the budget because requirement 5.4.4 keeps the estimate running without a forecast.",
      "Measured monthly availability of the subsystem (threshold 99.95%).",
      "Monitor a successful service check every minute and report monthly.", "Analysis", "C.0.2", "F.2.2", "Apportionment"),
    R("5.5.5", "operate with at least 500 enrolled accounts",
      "The Reference Data Subsystem shall operate without functional failure with at least 500 enrolled Commuter accounts.",
      ["3.4.3.2"], ["2.3.3"],
      "Equivalence: capacity cannot be divided among subsystems, because each trip on the path passes through every one of them. The same value applies to this subsystem.",
      "Number of enrolled accounts with which the subsystem operates without functional failure (target 500 or more).",
      "Run 500 test accounts through the entry task and confirm no functional failure.", "Test", "C.0.2", "F.2.2", "Equivalence"),
    R("5.5.6", "store and send only coarse location",
      "The Reference Data Subsystem shall limit every location that it stores or sends to Open-Meteo to coarse-area granularity.",
      ["3.4.5.2"], ["2.5.1", "2.3.5"],
      "Equivalence: the privacy limit is not a quantity to share out; every subsystem that handles a location must meet it in full.",
      "Number of stored or transmitted locations finer than a coarse area (target 0).",
      "Network and storage inspection of the pilot build.", "Inspection", "C.0.2", "F.2.2", "Equivalence"),
    R("5.5.7", "keep factor resolution of 0.001 grams per kilometre",
      "The Reference Data Subsystem shall store and return each emission factor with a resolution of at least 0.001 grams of CO2e per kilometre.",
      ["3.4.6.1"], ["2.4.1"],
      "Synthesis: the system must reproduce each reference result to the nearest gram, an error of at most 0.5 g. For a trip of up to 100 km, a factor rounded to 0.001 g/km changes the result by at most 100 km x 0.0005 g/km = 0.05 g, one tenth of that tolerance. The resolution is derived from the tolerance and the longest trip.",
      "Resolution of stored and returned factors (threshold 0.001 g CO2e per km).",
      "Compare stored factors with the published values; run the reference cases for trips up to 100 km.", "Test", "C.0.2", "F.2.2", "Synthesis"),
    R("5.5.8", "send the Route Service only the entered places",
      "The Reference Data Subsystem shall send the Route Service only the place text the Commuter entered and the coordinates resolved from it.",
      ["3.4.5.4"], ["2.1.18", "2.5.1"],
      "Equivalence: since model 11.0 the subsystem also resolves and suggests places (system requirement 3.3.1.17 is allocated to F.2.2), so it is the asset that calls the Route Service; the limit is a privacy constraint that cannot be divided and applies in full.",
      "Number of Route Service requests that carry data other than the entered place text and resolved coordinates (target 0).",
      "Capture the requests of a test run and inspect their fields.", "Inspection", "C.0.2", "F.2.2", "Equivalence"),
    R("5.5.9", "keep no record of who asked in the place cache",
      "The Reference Data Subsystem shall keep cached place and route answers without any record of which account asked.",
      ["3.4.5.7"], ["2.1.17", "2.1.18"],
      "Equivalence: the persistent place cache of model 11.0 lives in this subsystem; separating answers from accounts is a privacy limit that every holder of the cache must meet in full.",
      "Number of cache entries that identify the requesting account (target 0).",
      "Inspect the cache store after a multi-account test run.", "Inspection", "C.0.2", "F.2.2", "Equivalence"),
]
OMITTED = [
    ("3.4.2.2", "complete commute entry in 30 seconds", "Entry time is spent on the entry form; this subsystem has no user interface and is off the Commuter's path while the form is filled in."),
    ("3.4.4.1", "conform to WCAG 2.2 Level AA", "Applies to the entry and result views; the Reference Data Subsystem has no view."),
    ("3.4.5.1", "restrict access to individual trip records", "The subsystem keeps no trip records; it receives an entry, uses it and does not store it."),
    ("3.4.5.3", "suppress aggregate groups below 5", "Applies where aggregates are made, in the Reporting Subsystem."),
    ("3.4.5.5", "store passwords and invite codes only as hashes", "Accounts are managed by the Records Subsystem (3.3.1.15 is allocated to F.2.4)."),
    ("3.4.5.6", "lock log-in after repeated wrong passwords", "Log-in handling belongs to the Records and Entry Subsystems; this subsystem has no log-in."),
    ("3.4.6.2", "label route-based figures as estimates", "Labelling happens where the figure is estimated and shown, in the Estimation and Presentation Subsystems."),
    ("3.4.6.3", "state that bus times come from a timetable", "The timetable is read and shown by the Recommendation and Presentation Subsystems (3.3.1.13 is allocated to F.2.5)."),
]

# ------------------------------------------------------------------ flow-down budgets (educated guesses, see rationale of 5.5.x)
COST_BUDGET = [("C.0.0", 12), ("C.0.1", 12), ("C.0.2", 12), ("C.0.3", 10), ("C.0.4", 14), ("C.0.5", 8), ("C.0.6", 14), ("C.0.7", 8),
               ("Integration and test", 6), ("Management reserve", 4)]
TIME_BUDGET = [("C.0.1", 0.3), ("C.0.2", 1.2), ("C.0.3", 0.2), ("C.0.4", 0.3), ("C.0.5", 0.2), ("C.0.6", 0.5), ("Reserve", 0.3)]
AVAIL_BUDGET = [("C.0.0", 0.10), ("C.0.1", 0.07), ("C.0.2", 0.05), ("C.0.3", 0.03), ("C.0.4", 0.10), ("C.0.5", 0.03), ("C.0.6", 0.07), ("Reserve", 0.05)]

SECOND_LEVEL_PLAN = [   # third-level decomposition planned for the final assignment
    ("F.2.2.1 Load Emission Factors", "F.2.2.1.1 Read Factor Source, F.2.2.1.2 Validate Factor Attributes, F.2.2.1.3 Version Factor Set"),
    ("F.2.2.3 Request Weather Forecast", "F.2.2.3.1 Build Weather Request, F.2.2.3.2 Send Weather Request"),
]


MILESTONES = [   # date, milestone, owner / note, status on 2026-10-30
    ("2026-10-30", "Requirements baselined and model 11.0 imported; the web application implements UC.1, UC.3 and UC.4 with an automated test suite", "All subsystems", "Done"),
    ("2026-11-06", "Interfaces K.1 to K.24 frozen and written into docs/deployment.md; documents 4 and 5 reviewed", "C.0.1, C.0.4, all", "In progress"),
    ("2026-11-10", "Reference Data Subsystem passes the tests derived from its component specification", "C.0.2; Estimation depends on it", "Planned"),
    ("2026-11-12", "All other subsystems pass the tests derived from their design output requirements", "C.0.0, C.0.1, C.0.3 to C.0.7", "Planned"),
    ("2026-11-13", "**System integration date**: eight subsystems integrated, invited pilot accounts created (requirement 5.5.2)", "C.0 Integration", "Planned"),
    ("2026-11-16", "Pilot starts; four weeks of use before data collection closes", "C.0.0 Operations", "Planned"),
    ("2026-12-02", "System verification complete (response time, availability, access and suppression tests)", "C.0 Test", "Planned"),
    ("2026-12-11", "Pilot data collection closes; evaluation and report written", "C.0.7 Reporting", "Planned"),
    ("2026-12-18", "Pilot results due to the Company Sponsor (requirement 3.4.1.2)", "C.0.7 Reporting", "Planned"),
]


def all_reqs():
    return SDOR + INPUT + OUTPUT + INTERFACE + FUNCTIONAL + SYSWIDE


def check():
    problems = []
    nums = [r["num"] for r in all_reqs()]
    if len(nums) != len(set(nums)):
        problems.append("duplicate requirement numbers")
    if abs(sum(v for _, v in COST_BUDGET) - 100) > 1e-9:
        problems.append("cost budget does not sum to 100")
    if abs(sum(v for _, v in TIME_BUDGET) - 3.0) > 1e-9:
        problems.append("time budget does not sum to 3.0")
    if abs(sum(v for _, v in AVAIL_BUDGET) - 0.5) > 1e-9:
        problems.append("availability budget does not sum to 0.5")
    for r in all_reqs():
        if r["stmt"].count(" shall ") != 1:
            problems.append(f"{r['num']}: not exactly one shall")
    return problems


if __name__ == "__main__":
    print(check() or "OK", len(all_reqs()), "requirements")
