"""C.4 Explanation Model (UC.1.11, UC.3.5; requirement 2.1.10; risk TR.4; ADR 0011).

Two layers, so the model can never be the only author of what the Commuter reads:

1. A deterministic template sentence built from values C.2 already calculated (the contract; always correct).
2. Optionally a locally hosted language model that only *rephrases* that sentence. Its text is shown only if
   `guardrail.check_explanation` finds nothing in it that is not in the calculated result; otherwise, or when the
   model is unreachable, slow or answers in an unexpected shape, the template text is shown (a fallback that
   contains the failure) and the reason is counted in `explanation_stats()`.

Switch on with ECOCOMMUTE_EXPLAINER=local (see model_client.py). The default is the template.
"""
import os
import time
from dataclasses import dataclass

from src.model_trace import realizes

from .guardrail import Facts, check_explanation, direction_rules
from .model_client import ModelUnavailable, OllamaClient, build_prompt

BREAKER_SECONDS = 60.0  # after a failure the model is not asked again for this long (no 2 s wait on every page)

STATS = {"template": 0, "model": 0, "fallback_unavailable": 0, "fallback_rejected": 0, "fallback_skipped": 0}
_state = {"client": None, "down_until": 0.0, "clock": time.monotonic}


MODE_ALTERNATIVES = {"drive": "drive|driving|car", "walk": "walk|walking|foot", "bike": "bike|biking|cycle|cycling",
                     "bus": "bus", "scooter": "scooter", "carpool": "carpool|car"}


@dataclass(frozen=True)
class Outcome:
    text: str
    source: str            # "template" | "model" | "template-fallback"
    reason: str = ""       # why the fallback was used
    violations: tuple = ()
    latency_ms: float = 0.0


def set_client(client, clock=None):
    """Install a model client (tests, measurements) or None to go back to the environment setting."""
    _state["client"] = client
    _state["down_until"] = 0.0
    _state["clock"] = clock or time.monotonic


def reset_stats():
    for key in STATS:
        STATS[key] = 0
    _state["down_until"] = 0.0


def explanation_stats() -> dict:
    return dict(STATS)


def _client():
    if _state["client"] is not None:
        return _state["client"]
    if os.environ.get("ECOCOMMUTE_EXPLAINER", "template").strip().lower() != "local":
        return None
    try:
        _state["client"] = OllamaClient()
    except ModelUnavailable:
        return None
    return _state["client"]


def finalize(template_text: str, facts: Facts) -> Outcome:
    """Return what C.4 shows: the guarded model text, or the template text."""
    client = _client()
    if client is None:
        STATS["template"] += 1
        return Outcome(template_text, "template")
    if _state["clock"]() < _state["down_until"]:
        STATS["fallback_skipped"] += 1
        return Outcome(template_text, "template-fallback", "model recently unavailable")
    started = time.perf_counter()
    try:
        raw = client.generate(build_prompt(template_text))
    except ModelUnavailable as error:
        _state["down_until"] = _state["clock"]() + BREAKER_SECONDS
        STATS["fallback_unavailable"] += 1
        return Outcome(template_text, "template-fallback", f"model unavailable: {error}",
                       latency_ms=(time.perf_counter() - started) * 1000)
    elapsed = (time.perf_counter() - started) * 1000
    candidate = raw.strip().strip('"').strip() if isinstance(raw, str) else raw  # a non-text reply fails the check
    violations = check_explanation(candidate, facts)
    if violations:
        STATS["fallback_rejected"] += 1
        return Outcome(template_text, "template-fallback", "model text rejected", tuple(violations), elapsed)
    STATS["model"] += 1
    return Outcome(candidate, "model", latency_ms=elapsed)


# ---------------------------------------------------------------------------------------------- templates
def result_template(estimated_co2e_g, baseline_co2e_g, estimated_difference_g, factor_source, factor_version,
                    alternative_mode, alternative_reason) -> str:
    text = (
        f"Your trip is estimated at {estimated_co2e_g:g} g CO2e; driving the same distance "
        f"would be {baseline_co2e_g:g} g, an estimated difference of {estimated_difference_g:g} g "
        f"(an estimate, not verified avoided emissions). "
        f"Factor: {factor_source}, version {factor_version}."
    )
    if alternative_mode:
        text += f" Suggestion: {alternative_mode}. {alternative_reason}"
    else:
        text += f" {alternative_reason}"
    return text


def recommendation_template(chosen, fastest, met_limits: bool) -> str:
    if chosen.mode == "drive" and fastest.mode == "drive":
        return (
            "No greener way passed today's weather and time checks, so driving is the fallback: "
            f"{chosen.duration_min:g} min and an estimated {chosen.co2e_g:g} g CO2e (the driving baseline)."
        )
    text = (
        f"Recommended: {chosen.mode} - {chosen.duration_min:g} min and an estimated "
        f"{chosen.co2e_g:g} g CO2e"
    )
    if chosen.difference_g > 0:
        text += f", an estimated {chosen.difference_g:g} g less than driving"
    else:
        text += ", no estimated difference from driving"
    if chosen.mode == fastest.mode:
        text += "; it is also the fastest option."
    else:
        extra = chosen.duration_min - fastest.duration_min
        text += f"; {extra:g} min more than the fastest ({fastest.mode})."
    if not met_limits:
        text += " No option passed the weather and time checks, so this is the fastest one that was not ruled out."
    return text


# ---------------------------------------------------------------------------------------------- public contract
@realizes("UC.1.11")
def explain_result(
    estimated_co2e_g: float,
    baseline_co2e_g: float,
    estimated_difference_g: float,
    factor_source: str,
    factor_version: str,
    alternative_mode: str,
    alternative_reason: str,
) -> str:
    """UC.1.11 (part) Display Commute Result - plain-language explanation.

    Satisfies need 1.1.8 / requirement 2.1.10: the text states the estimated CO2e, the baseline and its
    difference, the factor source and version, and the recommendation reason, and nothing else. It receives
    only values that are already calculated, so it cannot calculate emissions, invent weather or override the
    eligibility rules. The model, when switched on, may rephrase but the guardrail keeps the facts fixed.
    """
    template = result_template(estimated_co2e_g, baseline_co2e_g, estimated_difference_g, factor_source,
                               factor_version, alternative_mode, alternative_reason)
    facts = Facts(
        allowed_numbers=(estimated_co2e_g, baseline_co2e_g, estimated_difference_g),
        required_numbers=(estimated_co2e_g, baseline_co2e_g, estimated_difference_g),
        allowed_modes=("drive", alternative_mode.split()[0].lower()) if alternative_mode else ("drive",),
        allowed_text=template,
        required_phrases=("estimate", str(factor_version)),
        forbidden=direction_rules(True, 0, estimated_difference_g)[-1:],  # the sign of the difference only
    )
    return finalize(template, facts).text


@realizes("UC.3.5")
def explain_recommendation(chosen, fastest, met_limits: bool) -> str:
    """Plain-language reason for a recommended mode.

    Receives rows the rules have already computed (a ModeComparison for the chosen mode and for the fastest
    one) and only restates their values; it cannot calculate, invent weather or change which mode was chosen.
    """
    return explain_recommendation_outcome(chosen, fastest, met_limits).text


def explain_recommendation_outcome(chosen, fastest, met_limits: bool) -> Outcome:
    template = recommendation_template(chosen, fastest, met_limits)
    facts = Facts(
        allowed_numbers=(chosen.duration_min, chosen.co2e_g, chosen.difference_g,
                         fastest.duration_min, chosen.duration_min - fastest.duration_min),
        required_numbers=(chosen.duration_min, chosen.co2e_g),
        allowed_modes=("drive", chosen.mode, fastest.mode),
        allowed_text=template,
        required_phrases=("estimate", MODE_ALTERNATIVES.get(chosen.mode, chosen.mode)),
        forbidden=direction_rules(chosen.mode == fastest.mode, chosen.duration_min - fastest.duration_min,
                                  chosen.difference_g),
    )
    return finalize(template, facts)
