"""Write docs/risks.md (the product risk register) from the one source of the ratings, docs/ch11/sim/model.py.

    python docs/ch11/build/make_risks_md.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import model as M  # noqa: E402

DETAIL = {
    "TR.16": dict(type="Performance, availability", phase="Design (build), Test, Operations",
                  xref="Flows IO.4 Weather Request, IO.5 Weather Forecast Data, IO.24 forecast query; F.2.2.3, F.2.2.4; C.0.2; X.3, X.6; requirements 3.4.2.1, 5.4.4, 5.5.3",
                  control="Selected: concurrent dispatch plus keep-alive (ADR 0012). Guardrail built: weather deadline 1.0 s, route deadline 1.2 s, labelled estimate as the fallback; counters in `plan.dispatch_stats()`.",
                  test="`tests/test_dispatch_guardrail.py`: slow forecast and slow routes return inside the deadline with a labelled fallback; counters; keep-alive never raises"),
    "TR.11": dict(type="Availability, cost", phase="Operations (pilot)",
                  xref="X.6 Route Service; C.0.2; requirements 5.5.5, 2.3.1; `route_adapter` cache and per-mode fallback",
                  control="Existing: per-mode labelled estimate, persistent route cache, 60 s cool-down after a refusal. Open: paid plan decision before the pilot. The quota ran out during the Chapter 11 measurements.",
                  test="`tests/test_routes.py` (fallback and cache)"),
    "TR.4": dict(type="Technical (trust, correctness)", phase="Design (build), Operations",
                 xref="Function F.2.6, UC.1.11 and UC.3.5; C.0.6 and the C.4 explanation model; IO.3 Commute Result and Advice; requirements 2.1.10 and 5.6.x",
                 control="Guardrail built (prevents the failure): the model may only rephrase, and `guardrail.check_explanation` accepts its text only if every figure, mode and comparison is in the calculated result; otherwise the template is shown (also a fallback). Measured: 20 of 40 raw outputs of qwen2.5:1.5b were rejected, 0 reached the page.",
                 test="`tests/test_c4_guardrail.py`: reversed comparison, invented figure, mode and weather, overclaim, markup, empty, non-text"),
    "TR.10": dict(type="Security, privacy", phase="Design, Operations",
                  xref="IO.1 Commuter Entries and Requests; IO.19 Trip Record Extract; F.2.4; requirements 2.5.1, 3.4.5.2, 3.4.5.7",
                  control="Existing: cache keeps no account; own position never cached. Open: confirmed trips keep start and destination labels.",
                  test="`tests/test_persistent_cache.py`"),
    "TR.1": dict(type="Technical (data validity)", phase="Design, Operations",
                 xref="IO.6 Reviewed Emission Factors; IO.14 Emission Factor Record; F.2.2.1, F.2.2.2; requirements 5.4.1, 5.4.2, 2.4.1",
                 control="Existing: EPA January 2025 factors reviewed 2026-11-09 (`docs/factor-review.md`); tailpipe only; scooter and carpool use labelled placeholders.",
                 test="`tests/test_functional_requirements.py` (5.4.x)"),
    "TR.17": dict(type="Availability, performance", phase="Operations",
                  xref="C.4 Explanation Model; UC.3.5; requirement 2.1.10",
                  control="Fallback built: 2.0 s timeout, template text, 60 s circuit breaker so a down model costs no waiting.",
                  test="`test_an_unavailable_model_falls_back_and_the_breaker_stops_asking`"),
    "TR.18": dict(type="Security", phase="Design, Operations",
                  xref="C.4 inputs: only values already calculated by C.2; interface contract in `src/c4_explanation_model/explainer.py`",
                  control="Guardrail by construction: the prompt is built from the template sentence only; place names, route sources and any text from a data source never enter it.",
                  test="`test_untrusted_text_never_reaches_the_prompt`"),
    "TR.19": dict(type="Security, privacy", phase="Design, Operations",
                  xref="C.4 model client; X.3 and X.6 calls; requirements 2.5.1, 3.4.5.2",
                  control="Guardrail built: the model client refuses any host that is not loopback unless an explicit variable is set. Known and accepted: the start place's coordinates go to Open-Meteo and OpenRouteService, which is how the product works.",
                  test="`test_a_model_on_another_machine_is_refused_so_trip_facts_do_not_leave`"),
    "TR.20": dict(type="Technical (interface)", phase="Operations",
                  xref="C.4 model client; contract of the model server's reply",
                  control="Guardrail built: a reply without a text `response` field, not JSON, or not text is treated as unavailable; the model name is configuration.",
                  test="`test_a_reply_without_a_response_field_is_schema_drift`"),
    "TR.21": dict(type="Supply, legal", phase="Design, Operations",
                  xref="Ollama server (open source), qwen2.5:1.5b (Apache License 2.0, checked on the Ollama library page), OpenRouteService host change (TR.11), TCAT feed (TR.13), Flask",
                  control="Open: pin versions in `requirements.txt`; the model is optional and off by default, so abandoning it removes no required function.",
                  test="None (a review item at each stage gate)"),
    "TR.22": dict(type="Process, technical", phase="Design (build)",
                  xref="`docs/prompt-log.md`; all components built with an assistant",
                  control="Every assisted change is logged with its prompt and sources; tests are written from the requirement text; a human reviews before merge. The Chapter 11 spike found a reversed comparison the first guardrail version missed; it was found by reading outputs, not by the assistant.",
                  test="The whole test suite (`python -m unittest discover -s tests -t .`)"),
    "TR.13": dict(type="Supply, legal", phase="Operations",
                  xref="TCAT GTFS feed; F.2.2; requirements 2.1.15, 2.4.4, 3.4.6.3",
                  control="Open: refresh with `python -m src.update_transit` before 19 December 2026; ask the agency about terms.",
                  test="`tests/test_transit.py`"),
    "TR.14": dict(type="Security, privacy", phase="Operations",
                  xref="Accounts store, C.0.4; requirements 3.3.1.15, 3.3.1.16, 3.4.5.5",
                  control="Existing: salted password hashes. Open: backup and deletion on request.", test="`tests/test_accounts.py`"),
    "TR.15": dict(type="Security", phase="Operations",
                  xref="C.1 log-in; requirements 2.3.8, 3.4.5.5, 3.4.5.6",
                  control="Existing: 15-minute lockout after 5 wrong passwords. Open: https tunnel for any shared network.", test="`tests/test_auth_web.py`"),
    "TR.7": dict(type="Availability", phase="Operations",
                 xref="X.5 Hosting Provider; IO.11 Hosting Service Status; requirements 2.2.4, 3.4.3.1, 5.5.4",
                 control="Open: no deployment yet; measure on the deployed host (Chapter 10 decision D9).", test="None yet"),
}

SCALES = """**Likelihood (L)**: 1 Rare (not expected in the pilot) / 2 Unlikely (could happen once) / 3 Possible (expected a few times) / 4 Likely (expected most weeks) / 5 Almost certain (already observed or expected every day).

**Impact scales** (each 1 to 5):

| Rating | Technical (performance, correctness, trust) | Schedule (pilot results due 18 December 2026) | Cost (system baseline $750,000) |
|---|---|---|---|
| 1 | No requirement affected | No delay | Less than $500 |
| 2 | A requirement degraded for a minority of uses, with a labelled fallback | Under 1 day | $500 to $2,000 |
| 3 | A requirement missed in part of the pilot | 1 to 3 days | $2,000 to $10,000 |
| 4 | A shall requirement not met or a wrong statement shown to a commuter | 3 to 7 days | $10,000 to $50,000 |
| 5 | The core value proposition fails, or personal data is exposed | More than 7 days or the pilot window is missed | Over $50,000 |

**Overall impact** = 0.5 x technical + 0.25 x schedule + 0.25 x cost (the sponsor's measures are mostly about whether the product works, so technical counts double). **Risk level** = L x overall impact (1 to 25). **Bands**: High 12 or more (red), Medium 6 to under 12 (yellow), Low under 6 (green). On the matrix the impact axis uses the overall impact rounded to the nearest whole number."""


def main():
    rows = M.risk_rows()
    lines = [
        "# Product risk register (EcoCommute, Team 6)",
        "",
        "Chapter 12 product build. Each risk has an identifier of the Innoslate model (`TR.n`, model 11.5: `docs/model/EcoCommute_11.5_C11-C12_analysis_risk.xml`) and is cross-referenced to the flows, functions, assets and requirements it touches. "
        "Rows marked **AI** are specific to an AI-enabled product or to building with an assistant. The report that explains the method is `docs/ch11/EcoCommute_Team6_Ch11-Ch12_System_Analysis_and_Risk_Assessment.docx`.",
        "",
        "**Likelihood and impact are the team's own engineering judgments**, made from the measurements named in each row. They were not generated by an assistant "
        "(the lab manual says a generated rating carries no information). Review them as a team and change a number in `docs/ch11/sim/model.py`, then rerun `python docs/ch11/build/make_risks_md.py`.",
        "",
        "## Scales and calculation",
        "",
        SCALES,
        "",
        "## Register, highest level first",
        "",
        "| ID | Risk | AI | Type | Phase | L | Tech | Sched | Cost | Overall impact | Level | Model cross-reference |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        d = DETAIL[r["id"]]
        lines.append(f"| {r['id']} | {r['short']} | {'AI' if r['ai'] else ''} | {d['type']} | {d['phase']} | {r['L']} | {r['tech']} | {r['sched']} | {r['cost']} | {r['overall']:.2f} | {r['level']:.2f} {r['band']} | {d['xref']} |")
    lines += ["", "## Controls and tests", "", "| ID | Control (guardrail prevents; fallback contains) | Test that exercises the failure path |", "|---|---|---|"]
    for r in rows:
        d = DETAIL[r["id"]]
        lines.append(f"| {r['id']} | {d['control']} | {d['test']} |")
    top = rows[0]
    lines += [
        "",
        "## Top risk and what was built",
        "",
        f"The top risk is **{top['id']} {top['short']}** (level {top['level']:.2f}). A **guardrail** was built, because the failure can be prevented: a call that has not answered by its deadline "
        "is dropped, so the plan is returned inside the 3-second display time, and the answer carries a **fallback** (a labelled estimate; the recommendation says weather rules were not applied). "
        "Both live in `src/c2_application_service/plan.py` and `src/c3_data_adapter/route_adapter.py`; the tests are in `tests/test_dispatch_guardrail.py`. "
        "The top AI-specific risk, TR.4, has its own guardrail and fallback in `src/c4_explanation_model/` (ADR 0011).",
        "",
        "Monitoring indicators, review points and the model's role in tracking them are in the Chapter 11 and 12 report (Section 9).",
    ]
    with open(os.path.join(ROOT, "docs", "risks.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote docs/risks.md", len(rows), "risks")


if __name__ == "__main__":
    main()
