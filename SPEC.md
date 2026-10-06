# SPEC.md - EcoCommute (C.0) Stakeholder Requirements Specification

Status: **draft, derived from the approved Stakeholder Requirements Document (SRD)** in the Team 6 report *Stakeholder Needs and Requirements Definition* (Oct 2026), not from a loose product idea. Each section keeps the SRD ID, so SPEC.md, the Innoslate model and the code share identifiers.

How to read a section: **Statement** = SRD text; **From need** = SND ID (and BMA need N-number in the report); **Acceptance criterion** = MOE target + validation criteria + method from SRD Tables 11-12; **Satisfied by (model)** = the `satisfies` relationships in the Innoslate export `docs/model/EcoCommute_10.6_C4-explanation-req.xml`; **Skeleton status** = what the Chapter 2 walking skeleton exercises (see [docs/traceability.md](docs/traceability.md)).

Requirement 2.1.10 and its need 1.1.8 (plain-language explanation, performed by C.4) were added after the Stakeholder Needs report and exist in the Innoslate model and here; the report still lists 27 requirements and 20 needs.

Not yet in this SPEC: system-level requirements for the SH.6/SH.7 needs (BMA N11), which the report defers to Architecture Definition; those will be added here as 3.x.x with a trace to the stakeholder requirements.

Open values needing sponsor confirmation: 3-second display time (2.1.2); minimum aggregate group size 5 (2.2.3).


## Group 2.1

### 2.1.1 - enable fast trip entry

- **Statement:** The EcoCommute system shall enable a Commuter to submit a commute log entry in 30 seconds or less for at least 80 percent of timed entry tasks.
- **Rationale:** Entry effort is the main barrier to repeated self-reporting; the target is the existing product target in the BMA (80% under 30 seconds).
- **From need:** 1.1.1
- **Acceptance criterion:** MOE - Percentage of timed entry tasks completed in 30 seconds or less (target 80% or more). Validation - Pilot usability session: at least 20 participants each log five trips on their own device; time from entry form ready to entry accepted; pass if 80% or more of tasks take 30 seconds or less. Method: Test.
- **Satisfied by (model):** I/O Commute Request, I/O Entry Form, I/O Entry Request, `UC.1.1`, `UC.1.2`, `UC.1.3`, `UC.1.4`
- **Skeleton status:** Partial - C.1 presents the entry fields and C.2 accepts one entry; no timing measurement and no real web form.

### 2.1.2 - display trip impact and baseline difference

- **Statement:** The EcoCommute system shall display the estimated CO2e of each accepted trip, in grams, together with its difference from the always-drive baseline within 3 seconds of entry submission.
- **Rationale:** Immediate, connected feedback is the core value proposition. The 3-second limit is a proposed responsiveness threshold to confirm in discovery.
- **From need:** 1.1.2
- **Acceptance criterion:** MOE - Percentage of surveyed Commuters who correctly explain the estimate and the baseline difference (target 80% or more). Validation - Structured comprehension questions after use in the pilot; disclose sample size and scoring; confirm display time with a timing test on three reference devices. Method: Test.
- **Satisfied by (model):** I/O Commute Impact Result, `UC.1`, `UC.1.11`, `UC.1.12`, `UC.1.8`, `UC.1.9`
- **Skeleton status:** Exercised - Result shows estimated CO2e and difference from the always-drive baseline; 3-second display time is not measured.

### 2.1.3 - disclose estimation method

- **Statement:** The EcoCommute system shall display, with each trip result, the emission factor source, the factor version and the distance convention used to calculate it.
- **Rationale:** People trust an estimate only if they can see what it rests on; also supports reviewer traceability.
- **From need:** 1.1.3
- **Acceptance criterion:** MOE - Percentage of displayed trip results that carry source, version and distance convention (target 100%). Validation - Inspection of a random sample of 50 displayed results in the pilot build; pass if every sampled result shows all three items. Method: Inspection.
- **Satisfied by (model):** `UC.1.11`
- **Skeleton status:** Exercised - Result shows factor source, factor version and distance convention (values are stub placeholders).

### 2.1.4 - recommend a feasible lower-emission option

- **Statement:** The EcoCommute system shall provide, for each accepted trip with an eligible lower-emission option, one alternative travel mode with a stated reason based on trip distance, forecast weather and the Commuter's feasibility settings.
- **Rationale:** Advice only changes behaviour if it fits the Commuter's situation; a stated reason lets the Commuter judge it.
- **From need:** 1.1.4
- **Acceptance criterion:** MOE - Percentage of surveyed Commuters who rate the advice feasible (target 80% or more). Validation - Post-result survey in the pilot; report opt-outs and non-response; rule review against the product description rule (distance under 3 km and no rain). Method: Demonstration.
- **Satisfied by (model):** I/O Weather Forecast, I/O Weather Query, `UC.1`, `UC.1.10`, `UC.1.6`, `UC.1.7`
- **Skeleton status:** Exercised - Rule in C.2 `evaluate_alternatives` uses distance, stubbed forecast weather and feasibility settings.

### 2.1.5 - exclude infeasible modes

- **Statement:** The EcoCommute system shall exclude from its recommendations every travel mode that the Commuter has marked as not feasible.
- **Rationale:** Prevents advice the Commuter has already ruled out, such as cycling with equipment or when carrying children.
- **From need:** 1.1.4
- **Acceptance criterion:** MOE - Number of recommendations that include a mode marked not feasible (target 0). Validation - Rule test set covering every combination of marked-not-feasible modes; pass if no recommendation contains an excluded mode. Method: Test.
- **Satisfied by (model):** `UC.1.10`
- **Skeleton status:** Exercised - Test `test_infeasible_mode_is_never_recommended`.

### 2.1.6 - display trends and cumulative difference

- **Statement:** The EcoCommute system shall display each Commuter's weekly and monthly CO2e totals and cumulative CO2e difference from the always-drive baseline.
- **Rationale:** Seeing progress over time is what keeps a Commuter logging after the first week.
- **From need:** 1.1.5
- **Acceptance criterion:** MOE - Weekly active use after eight weeks (target 40% or more of enrolled Commuters). Validation - Cohort report: a Commuter is active if there is at least one accepted log in the preceding seven days; denominator is all enrolled Commuters; measured at week eight. Method: Analysis.
- **Satisfied by (model):** `UC.1.9`
- **Skeleton status:** Partial - Stub trend sums stored trips; no weekly/monthly windowing.

### 2.1.7 - restrict access to individual trip records

- **Statement:** The EcoCommute system shall restrict access to each Commuter's individual trip records to that Commuter.
- **Rationale:** Privacy control is a condition of participation for Commuters and a legal and reputational risk for the sponsors.
- **From need:** 1.1.6, 1.2.2
- **Acceptance criterion:** MOE - Number of individual trip records exposed to any other role in access tests (target 0). Validation - Role-based access test matrix across Commuter, Pilot Administrator and company staff roles; residual privacy-risk review by the assurance reviewers. Method: Test.
- **Satisfied by (model):** `OP.1`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.1.8 - delete trip records on request

- **Statement:** The EcoCommute system shall permanently delete all of a Commuter's trip records upon the Commuter's deletion request.
- **Rationale:** Control over one's own data builds the trust needed for voluntary participation.
- **From need:** 1.1.6
- **Acceptance criterion:** MOE - Percentage of deletion requests that leave no identifiable trip record (target 100%). Validation - Deletion test: create records for test accounts, request deletion, query storage and backups in scope; pass if none remain. Method: Test.
- **Satisfied by (model):** `OP.1`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.1.9 - conform to accessibility standard

- **Statement:** The EcoCommute system shall conform to WCAG 2.2 Level AA for the commute entry and result views.
- **Rationale:** Inclusive access is a charter expectation and a pilot-entry condition.
- **From need:** 1.1.7, 1.5.3
- **Acceptance criterion:** MOE - Number of unresolved WCAG 2.2 Level AA failures in the entry and result views (target 0). Validation - Accessibility audit of both views plus keyboard and assistive-technology tasks; pass if no failures remain open. Method: Inspection.
- **Satisfied by (model):** `UC.1.11`, `UC.1.2`
- **Skeleton status:** Not in skeleton - No web UI yet.

### 2.1.10 - explain result from calculated facts

- **Statement:** The EcoCommute system shall display with each trip result a plain-language explanation that states only facts contained in the calculated result: the estimated CO2e, the baseline difference, the factor source and version, and the recommendation reason.
- **Rationale:** Commuters read a result more easily in words, but unsupported generated text would reduce trust and could overclaim savings (BMA risk R8); the explanation may only restate calculated, rule-approved facts and must not calculate emissions, invent weather or override eligibility rules. Added after the Stakeholder Needs report; exists in the Innoslate model and SPEC.md.
- **From need:** 1.1.8
- **Acceptance criterion:** MOE - Number of sampled explanations that contain a figure, weather condition or travel mode not present in the calculated result (target 0). Validation - Inspect a random sample of 50 displayed explanations in the pilot build, comparing each field by field with the calculated result; pass if none contains an unsupported figure, condition or mode. Method: Inspection.
- **Satisfied by (model):** `UC.1.11`
- **Skeleton status:** Exercised - C.4 `explain_result` receives only calculated values (estimate, baseline, difference, factor source and version, reason) and returns a template sentence (stub; no language model). Tests `test_explanation_contains_required_facts` and `test_explanation_states_only_calculated_facts`.


## Group 2.2

### 2.2.1 - provide participation summary

- **Statement:** The EcoCommute system shall provide an authorized Pilot Administrator with the enrollment count, the weekly active count and the total CO2e for a selected reporting period.
- **Rationale:** The sponsor needs engagement evidence for its own reporting; these three figures are the minimum the BMA identifies.
- **From need:** 1.2.1
- **Acceptance criterion:** MOE - Percentage of the sponsor's reporting questions that the summary answers or explicitly defers (target 100%). Validation - Review the approved summary against the sponsor's list of reporting questions at pilot readiness; record deferrals with sponsor agreement. Method: Demonstration.
- **Satisfied by (model):** `UC.2`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.2.2 - exclude individual data from summaries

- **Statement:** The EcoCommute system shall exclude individual Commuter identifiers and trip records from every institutional summary.
- **Rationale:** Institutions should see program-level evidence only, which keeps individual privacy and limits the sponsor's exposure.
- **From need:** 1.2.2
- **Acceptance criterion:** MOE - Number of individual identifiers or trip records found in institutional outputs (target 0). Validation - Output inspection and access tests on every summary type before release. Method: Inspection.
- **Satisfied by (model):** `UC.2`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.2.3 - suppress small groups

- **Statement:** The EcoCommute system shall suppress any aggregate group that contains fewer than 5 Commuters.
- **Rationale:** Small groups can be re-identified from aggregates. The value 5 is a proposed default because the BMA leaves the threshold open; the pilot sponsor must confirm it.
- **From need:** 1.2.2
- **Acceptance criterion:** MOE - Number of reported groups with fewer than 5 Commuters (target 0). Validation - Aggregation test with seeded groups of sizes 1 to 10; pass if no group below the threshold is reported; sponsor confirms threshold. Method: Test.
- **Satisfied by (model):** `UC.2`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.2.4 - maintain service availability

- **Statement:** The EcoCommute system shall maintain an availability of at least 99.5 percent during each month of the pilot.
- **Rationale:** Reliable access protects the logging habit and the sponsor's credibility; the value is the existing product target.
- **From need:** 1.2.3
- **Acceptance criterion:** MOE - Measured monthly availability (target 99.5% or more). Validation - Define the measurement period and exclusions before the pilot; monitor a successful service check every minute; report monthly. Method: Analysis.
- **Satisfied by (model):** `OP.2`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).


## Group 2.3

### 2.3.1 - stay within the baseline cost

- **Statement:** The EcoCommute system shall cost no more than $750,000 to develop and deploy.
- **Rationale:** The baseline budget in the project charter limits the investment the Company Sponsor has approved.
- **From need:** 1.3.1
- **Acceptance criterion:** MOE - Cost variance against the $750,000 baseline (target 0% or less). Validation - Sponsor reviews cost forecast, scope variance and evidence at each stage gate. Method: Analysis.
- **Satisfied by (model):** `OP.5`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.2 - record accepted-log events

- **Statement:** The EcoCommute system shall record a timestamped event for every accepted trip log so that weekly active use can be computed for each enrolled Commuter.
- **Rationale:** The launch decision depends on engagement evidence, which can only be computed if usage events are recorded.
- **From need:** 1.3.2
- **Acceptance criterion:** MOE - Percentage of enrolled Commuters whose weekly active status can be computed from recorded events (target 100%). Validation - Reconcile the event log with accepted entries for test accounts; pass if every accepted entry has exactly one event. Method: Test.
- **Satisfied by (model):** `OP.3`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.3 - operate with the pilot cohort

- **Statement:** The EcoCommute system shall operate without functional failure with at least 500 enrolled Commuter accounts.
- **Rationale:** 500 enrolled users is the existing pilot participation target in the BMA and must be technically possible.
- **From need:** 1.3.2
- **Acceptance criterion:** MOE - Number of enrolled Commuter accounts with which the system operates without functional failure (target 500 or more). Validation - Create 500 test accounts and run the entry and summary tasks; pass if no functional failures occur. Method: Test.
- **Satisfied by (model):** `OP.2`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.4 - report pilot results

- **Statement:** The EcoCommute system shall provide the Company Sponsor with pilot results for each stakeholder measure of effectiveness before June 30, 2027.
- **Rationale:** The launch decision is scheduled for June 30, 2027 and needs evidence first.
- **From need:** 1.3.2
- **Acceptance criterion:** MOE - Number of measures of effectiveness with reported pilot results at the decision date (target equal to the number defined). Validation - Evaluation report checked against the MOE list at the launch-decision gate. Method: Inspection.
- **Satisfied by (model):** `OP.3`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.5 - avoid device location traces

- **Statement:** The EcoCommute system shall not collect location traces from Commuter devices.
- **Rationale:** Passive GPS is excluded from the baseline scope; collecting it would raise cost and privacy exposure.
- **From need:** 1.3.3
- **Acceptance criterion:** MOE - Number of device location traces collected (target 0). Validation - Network and storage inspection of the pilot build; pass if no location traces are transmitted or stored. Method: Inspection.
- **Satisfied by (model):** `OP.1`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.6 - delete identifiable records at retirement

- **Statement:** The EcoCommute system shall permanently delete all identifiable Commuter records at service retirement.
- **Rationale:** Prevents the company from carrying personal data after the program ends.
- **From need:** 1.3.4
- **Acceptance criterion:** MOE - Percentage of identifiable Commuter records deleted at retirement (target 100%). Validation - Disposal rehearsal on a copy of the pilot data before retirement; sponsor-approved retention review. Method: Test.
- **Satisfied by (model):** `OP.4`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.3.7 - export approved aggregates at retirement

- **Statement:** The EcoCommute system shall export the approved aggregate summaries at service retirement.
- **Rationale:** Preserves program evidence for the institution without keeping personal data.
- **From need:** 1.3.4
- **Acceptance criterion:** MOE - Percentage of approved aggregate summaries exported at retirement (target 100%). Validation - Disposal rehearsal verifies the export file against the approved summary list. Method: Test.
- **Satisfied by (model):** `OP.4`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).


## Group 2.4

### 2.4.1 - use reviewed emission factors

- **Statement:** The EcoCommute system shall calculate trip CO2e using only reviewed emission factors that record source, units, geography and version.
- **Rationale:** Traceable factors make results defensible and allow later review.
- **From need:** 1.4.1
- **Acceptance criterion:** MOE - Percentage of calculated trips whose factor record is complete (target 100%). Validation - Audit of factor store and a sample of calculated trips; confirm source, units, geography and version are present. Method: Inspection.
- **Satisfied by (model):** `UC.1.5`
- **Skeleton status:** Partial - Factor record carries source/units/geography/version, but the values are placeholders, not reviewed factors.

### 2.4.2 - reproduce reference cases

- **Statement:** The EcoCommute system shall reproduce each agreed reference-case CO2e result to the nearest gram.
- **Rationale:** Reference cases give an independent check on the calculation, including units and occupancy handling.
- **From need:** 1.4.1
- **Acceptance criterion:** MOE - Percentage of agreed reference cases reproduced (target 100%). Validation - Reviewers calculate the reference cases independently and compare with system output. Method: Test.
- **Satisfied by (model):** `UC.1.8`
- **Skeleton status:** Partial - Distance x factor calculation exists; no agreed reference cases yet.

### 2.4.3 - calculate a declared baseline

- **Statement:** The EcoCommute system shall calculate the always-drive baseline from the trip distance, a declared vehicle emission factor and a declared occupancy.
- **Rationale:** A baseline is fair only if its assumptions are stated and applied consistently.
- **From need:** 1.4.2
- **Acceptance criterion:** MOE - Percentage of audited trips whose baseline matches the declared assumptions (target 100%). Validation - Recalculate the baseline for a sample of 50 trips and compare with system output. Method: Analysis.
- **Satisfied by (model):** `UC.1.9`
- **Skeleton status:** Exercised - Baseline = same distance x declared drive factor, occupancy 1 (test `test_baseline_difference_for_greener_mode`).

### 2.4.4 - label differences as estimates

- **Statement:** The EcoCommute system shall label each baseline difference as an estimated difference.
- **Rationale:** The difference is a modeled counterfactual, not verified avoided emissions.
- **From need:** 1.4.3
- **Acceptance criterion:** MOE - Percentage of displayed baseline differences labelled as estimated (target 100%). Validation - Inspection of all views that show a baseline difference. Method: Inspection.
- **Satisfied by (model):** `UC.1.11`
- **Skeleton status:** Exercised - Difference is labelled 'estimated difference'.


## Group 2.5

### 2.5.1 - store only coarse location

- **Statement:** The EcoCommute system shall store trip location only at coarse-area granularity.
- **Rationale:** Precise coordinates are unnecessary for the product and increase harm if records leak.
- **From need:** 1.5.1
- **Acceptance criterion:** MOE - Number of stored records that contain precise coordinates (target 0). Validation - Database inspection on the pilot build and a field-level data review. Method: Inspection.
- **Satisfied by (model):** `OP.1`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.5.2 - record consent before storing trips

- **Statement:** The EcoCommute system shall require a recorded Commuter consent before storing the first trip record.
- **Rationale:** Shows that participation is voluntary and informed.
- **From need:** 1.5.2
- **Acceptance criterion:** MOE - Number of stored trip records without prior recorded consent (target 0). Validation - Test flow: attempt to store a trip without consent and with consent; audit stored records against the consent log. Method: Test.
- **Satisfied by (model):** `OP.1`
- **Skeleton status:** Not in skeleton - Outside the UC.1 nominal path (institutional, operational or retirement behavior).

### 2.5.3 - pass assistive-technology walkthrough

- **Statement:** The EcoCommute system shall allow a keyboard-only user and a screen-reader user to complete the commute entry task before pilot readiness.
- **Rationale:** Verifies accessibility with real tasks before real users are enrolled.
- **From need:** 1.5.3
- **Acceptance criterion:** MOE - Number of unresolved critical task barriers for keyboard and screen-reader users (target 0). Validation - Moderated walkthrough with at least one keyboard-only and one screen-reader user; barriers logged and resolved. Method: Demonstration.
- **Satisfied by (model):** `UC.1.2`, `UC.1.3`
- **Skeleton status:** Not in skeleton - No web UI yet.
