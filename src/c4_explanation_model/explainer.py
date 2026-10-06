from src.model_trace import realizes


@realizes("UC.1.11")
def explain_result(
    estimated_co2e_g: float,
    baseline_co2e_g: float,
    alternative_mode: str,
    alternative_reason: str,
) -> str:
    """UC.1.11 (part) Display Commute Result - plain-language explanation.

    Satisfies need 1.1.8 / requirement 2.1.10: the text states only facts passed
    in from the already-calculated result (estimate, baseline, recommendation
    reason). It cannot calculate emissions, invent weather or override the
    eligibility rules because it receives no raw inputs.

    STUB (BMA Section 7.9): a fixed sentence template instead of a call to a
    local language model. A real model must keep the same contract.
    """
    text = (
        f"Your trip is estimated at {estimated_co2e_g:g} g CO2e; driving the same distance "
        f"would be {baseline_co2e_g:g} g. The difference is an estimate, not verified avoided emissions."
    )
    if alternative_mode:
        text += f" Suggestion: {alternative_mode}. {alternative_reason}"
    else:
        text += f" {alternative_reason}"
    return text
