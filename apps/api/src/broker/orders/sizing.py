"""ATR-based reference levels and risk-based position size for order previews.

Pure functions, no I/O. The numbers are *descriptive* context shown on a
preview — a volatility-scaled stop distance, a reference level, and the share
count at which hitting that stop would cost ``risk_per_trade`` of equity.
They are not recommendations to buy, sell, or size a trade any particular way;
the human chooses the order and approves it.
"""
from __future__ import annotations

import math


def atr_stop_and_target(
    entry: float,
    atr: float | None,
    stop_multiple: float = 2.0,
    target_multiple: float = 3.0,
) -> tuple[float, float] | None:
    """(entry - stop_multiple*ATR, entry + target_multiple*ATR), or None when
    ATR is unknown/degenerate or the stop would not be a positive price."""
    if atr is None or math.isnan(atr) or atr <= 0 or entry <= 0:
        return None
    stop = entry - stop_multiple * atr
    if stop <= 0:
        return None
    return stop, entry + target_multiple * atr


def risk_sized_shares(
    entry: float,
    stop: float,
    equity: float,
    risk_per_trade: float,
    max_position_value: float,
) -> int:
    """Shares such that a move from entry to stop costs ``risk_per_trade`` of
    equity: floor(equity * risk_per_trade / (entry - stop)), capped so the
    position value stays within ``max_position_value`` (the max-position rule's
    dollar room, net of any existing position)."""
    per_share_risk = entry - stop
    if per_share_risk <= 0 or equity <= 0 or entry <= 0:
        return 0
    shares = math.floor(equity * risk_per_trade / per_share_risk)
    cap = math.floor(max(max_position_value, 0.0) / entry)
    return min(shares, cap)
