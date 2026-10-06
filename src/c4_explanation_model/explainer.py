from src.model_trace import realizes


@realizes("UC.1.11")
def explain_result() -> str:
    """UC.1.11 (part) Display Commute Result - explanation text.

    STUB (BMA Section 7.9): returns a hard-coded sentence instead of calling a
    local language model. The real C.4 may only explain an already-calculated
    result; it must not calculate emissions, invent weather or override the
    eligibility rules. NOTE: no stakeholder need/requirement covers this
    explanation yet - see docs/traceability.md, open item O-1.
    """
    return (
        "This estimate uses the distance you entered and a stored emission factor. "
        "The difference compares your trip with driving the same distance; it is an "
        "estimate, not verified avoided emissions."
    )
