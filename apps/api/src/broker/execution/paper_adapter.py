"""Simulated fills for approved order previews.

MVP fill model: fills exactly at the requested limit price. No slippage or
partial-fill simulation — Milestone E's IBKR adapter will be the second
implementation this seam exists for; don't generalize further until then.
"""


def simulate_fill(limit_price: float) -> float:
    return limit_price
