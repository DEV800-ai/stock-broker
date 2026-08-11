"""Simulated fills for approved order previews.

Fill model: fills carry adverse slippage (worse than the limit price, both
directions) and, when the requested size is large relative to average daily
volume, either a partial fill or an outright rejection — so paper performance
can't look better than a real market would have given for that size. Partial
fills are only modeled on entry (BUY); exits (SELL) either fill in full
(with slippage) or are rejected, since PaperTrade has no way to represent a
position closed across two different exit prices/dates without splitting the
trade — that's a bigger schema change than this pass is scoped for.
Next-bar fill (waiting for the following bar's price) is not modeled either:
this simulator only ever prices at approval time and has no notion of a
"next bar" relative to that instant.
"""
from broker.config import settings
from broker.execution.base import BrokerAdapter, FillResult


def simulate_fill(
    action: str,
    limit_price: float,
    requested_shares: int,
    avg_daily_volume: float | None,
    allow_partial: bool = True,
) -> FillResult:
    theoretical_price = limit_price
    adv_pct = (requested_shares / avg_daily_volume) if avg_daily_volume else None

    if adv_pct is not None and adv_pct >= settings.paper_fill_reject_adv_pct:
        return FillResult(status="rejected", filled_shares=0, fill_price=None, theoretical_price=theoretical_price)

    filled_shares = requested_shares
    if allow_partial and adv_pct is not None and adv_pct >= settings.paper_fill_partial_adv_pct:
        # Linearly shrink the fill between the partial threshold and the reject threshold.
        span = settings.paper_fill_reject_adv_pct - settings.paper_fill_partial_adv_pct
        progress = (adv_pct - settings.paper_fill_partial_adv_pct) / span if span > 0 else 1.0
        fill_ratio = max(settings.paper_fill_min_partial_ratio, 1.0 - progress)
        filled_shares = max(1, int(requested_shares * fill_ratio))

    slippage = limit_price * (settings.paper_fill_slippage_bps / 10_000)
    fill_price = limit_price + slippage if action == "BUY" else limit_price - slippage

    status = "filled" if filled_shares == requested_shares else "partial"
    return FillResult(status=status, filled_shares=filled_shares, fill_price=fill_price, theoretical_price=theoretical_price)


class PaperAdapter(BrokerAdapter):
    """BrokerAdapter implementation backing paper trading. See execution/base.py."""

    def submit_order(
        self,
        action: str,
        ticker: str,
        limit_price: float,
        requested_shares: int,
        avg_daily_volume: float | None,
        allow_partial: bool,
    ) -> FillResult:
        return simulate_fill(action, limit_price, requested_shares, avg_daily_volume, allow_partial=allow_partial)
