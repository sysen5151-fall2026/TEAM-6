from src.model_trace import realizes


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

    Satisfies need 1.1.8 / requirement 2.1.10: the text states the estimated CO2e,
    the baseline and its difference, the factor source and version, and the
    recommendation reason, and nothing else. It receives only values that are
    already calculated, so it cannot calculate emissions, invent weather or
    override the eligibility rules.

    STUB (BMA Section 7.9): a fixed sentence template instead of a call to a
    local language model. A real model must keep the same contract.
    """
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


@realizes("UC.3.5")
def explain_recommendation(chosen, fastest, met_limits: bool) -> str:
    """Plain-language reason for a recommended mode.

    Receives rows the rules have already computed (a ModeComparison for the
    chosen mode and for the fastest one) and only restates their values; it
    cannot calculate, invent weather or change which mode was chosen.

    STUB (BMA Section 7.9): a fixed sentence template instead of a language model.
    """
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
        text += " No option met all of your limits, so this is the fastest one you have not ruled out."
    return text
