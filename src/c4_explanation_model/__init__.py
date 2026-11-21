"""C.4 Explanation Model - plain-language explanations of already-calculated results."""
from .explainer import explain_recommendation, explain_recommendation_outcome, explain_result, explanation_stats
from .guardrail import Facts, check_explanation

__all__ = ["explain_recommendation", "explain_recommendation_outcome", "explain_result", "explanation_stats",
           "Facts", "check_explanation"]
