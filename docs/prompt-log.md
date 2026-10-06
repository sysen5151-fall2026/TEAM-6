# GenAI prompt / provenance log

Rule: every GenAI-assisted change is logged here with the tool, the (constrained) prompt, the source text it was constrained by, what it produced, and the human review. Do not use a broad prompt to generate the whole project.

## Entry 001 - 2026-10-05 - Repository restructure and UC.1 walking skeleton

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen (team member) |
| Branch | `feat/walking-skeleton-uc1` |
| Prompt (summary of the user's request, originally written in Chinese) | Fix the two weakest Milestone 1 rows (Walking Skeleton, Model-to-Product Linkage): restructure the repo per BMA Section 7.9 (README with OpsCon, docs/context.md, SPEC.md, prompt log) and build one stubbed end-to-end UC.1 path; choose the stack that is easiest for a Python-leaning team. |
| Constraining sources given to the assistant | BMA Sections 4.3, 7.1, 7.3, 7.7, 7.9; Stakeholder Needs and Requirements report Tables 10-12 (SRD); Innoslate export `EcoCommute 10.4.xml` (original source export at that time; superseded by 10.5 and 10.6) (requirement `satisfies` relationships); Milestone 1 criteria PDF |
| What the assistant produced | `README.md` (OpsCon copied verbatim from BMA 7.1), `docs/context.md`, `docs/walking-skeleton.md`, `docs/traceability.md`, `docs/environment.md`, `docs/adr/0001-initial-toolchain.md`, `SPEC.md` (generated from the SRD tables by script), `src/` participants C.1-C.4, X.1 simulation, X.3 stub, `src/model_trace.py`, `tests/`; removed the generic `math_utils` starter files and old `src/main.py` |
| Constraints applied | Stub boundaries per BMA 7.9 (hard-coded explanation, no real source access, live model calls, retries, exception handling or runtime logging); code and tests tagged with UC.1 action IDs and SRD IDs; placeholder emission factors labelled as not reviewed |
| Not generated / not claimed | Reviewed emission factors; a working local language model; a web UI; off-nominal behavior |
| Human review | **Pending.** Reviewer name and date: ____________ . Checklist: (1) OpsCon in README matches BMA 7.1; (2) context.md matches BMA 4.3; (3) SPEC statements match the SRD; (4) call order matches the Sequence Diagram; (5) `python -m src.main` and tests pass on a second machine. |

## Entry 002 - 2026-10-05 - C.4 explanation need/requirement, model 10.6

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `feat/c4-explanation-requirement` |
| Prompt (summary, originally Chinese) | Add one requirement for C.4 and give an updated Innoslate XML; update the Canvas submission. |
| Constraining sources | Entry 001 outputs; Innoslate export `EcoCommute 10.5_C1-C4`; SND/SRD wording conventions (need: "I need ... so that ..."; requirement: one "shall", measurable MOE, validation, method); BMA 7.9 (C.4 may only explain a calculated result) and risk R8 |
| What it produced | Need 1.1.8 and requirement 2.1.10 with trace/satisfy/perform links in `docs/model/EcoCommute_10.6_C4-explanation-req.xml` (script-patched XML, 2 entities and 12 relationships added, nothing removed); `explain_result()` now takes only calculated values; new test; regenerated SPEC.md (28 requirements); doc updates |
| Not claimed | The Stakeholder Needs report (docx/pdf) is not updated: it still says 20 needs and 27 requirements |
| Human review | **Pending.** Reviewer and date: ____________ . Check the requirement wording and the XML import (10.5 import verified by screenshot; 10.6 import pending). |

## Entry 003 - 2026-10-05 - Fixes after an external review of the Canvas submission

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `fix/model-status-and-2-1-10-test` |
| Prompt (summary, originally Chinese) | Evaluate a second reviewer's comments on the submission; adopt the reasonable ones. |
| Constraining sources | Reviewer comments; Innoslate Intelligence screenshot of the imported 10.5 (C.1-C.4) model; Entry 002 outputs |
| What it produced | `explain_result()` now also takes the estimated difference, factor source and version, so the explanation states every fact named in requirement 2.1.10; new test `test_explanation_contains_required_facts`; `tests/test_model_linkage.py` now reads the UC.1 actions from the exported XML instead of a hard-coded list; docs wording corrected (import status, what the linkage test checks); screenshot saved as `docs/model/intelligence-10.5-c1-c4.webp`; `.gitignore` excludes the Canvas submission files |
| Not claimed | 10.6 has not been imported into Innoslate or run through Intelligence |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry 004 - 2026-10-06 - Record the Innoslate import of model 10.6

| Field | Value |
|---|---|
| Tool / model | Claude Code (Claude desktop app), Claude Sonnet 5.5 |
| Requested by | Luyu Chen |
| Branch | `docs/model-10-6-verified` |
| Prompt (summary, originally Chinese) | The team imported 10.6 into Innoslate; here is the Intelligence screenshot; record it. |
| Constraining sources | Team screenshot of the Innoslate Intelligence dashboard (116 entities, 34 requirements, no errors, 81% pass rate) |
| What it produced | `docs/model/intelligence-10.6.webp`; import status updated in `docs/context.md` and `docs/traceability.md` (O-7 closed) |
| Not claimed | Diagrams still show C.0 only until they are redrawn; no human has yet reviewed the 10.6 requirement wording |
| Human review | **Pending.** Reviewer and date: ____________ . |

## Entry template

| Field | Value |
|---|---|
| Date / tool / model | |
| Requested by / branch | |
| Prompt (verbatim or summary) | |
| Constraining requirement/spec text (IDs) | |
| What it produced (files) | |
| Human review (who, when, what changed) | |
