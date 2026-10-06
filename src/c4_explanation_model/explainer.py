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
