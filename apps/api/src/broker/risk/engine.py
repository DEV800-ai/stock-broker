"""Deterministic risk policy engine.

Combines all rules in risk/rules.py into a single verdict. No LLM in the
loop — this module decides what is *eligible* to reach a human for approval,
not whether an order actually gets placed. Even an "approved" verdict still
requires human sign-off in MVP (see docs/SIGNAL_ALPHA_DESIGN.md §8).
"""
from broker.risk.rules import RULES
from broker.risk.types import RiskContext, RiskEvaluation

# Highest-priority severity wins when multiple rules fail at once.
_SEVERITY_PRECEDENCE = ["block", "paper_only", "needs_smaller_size", "needs_manual_review"]

_SEVERITY_TO_VERDICT = {
    "block": "blocked",
    "paper_only": "paper_only",
    "needs_smaller_size": "needs_smaller_size",
    "needs_manual_review": "needs_manual_review",
}


def evaluate(ctx: RiskContext) -> RiskEvaluation:
    results = [rule(ctx) for rule in RULES]
    failed_severities = {r.severity for r in results if not r.passed}

    for severity in _SEVERITY_PRECEDENCE:
        if severity in failed_severities:
            return RiskEvaluation(verdict=_SEVERITY_TO_VERDICT[severity], results=results)

    return RiskEvaluation(verdict="approved", results=results)
