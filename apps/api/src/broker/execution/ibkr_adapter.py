"""Live execution adapter — structural placeholder only.

Per CLAUDE.md ("No live trading code until Phase 4"), this class does not call
IBKRClient.place_order anywhere. It exists now so BrokerAdapter has a second,
real implementation to prove the interface, and so Phase 4 has an isolated
seam to fill in — rather than someone wiring IBKRClient.place_order directly
into orders/service.py later, bypassing this boundary and ENABLE_LIVE_TRADING.
submit_order() always raises; get_broker_adapter() in orders/service.py never
returns this class today.
"""
from broker.config import settings
from broker.execution.base import BrokerAdapter, FillResult


class LiveTradingDisabled(Exception):
    pass


class IBKRAdapter(BrokerAdapter):
    def submit_order(
        self,
        action: str,
        ticker: str,
        limit_price: float,
        requested_shares: int,
        avg_daily_volume: float | None,
        allow_partial: bool,
    ) -> FillResult:
        if not settings.enable_live_trading:
            raise LiveTradingDisabled("ENABLE_LIVE_TRADING is false; live execution is not available")
        raise NotImplementedError(
            "Live order execution is Phase 4 scope (CLAUDE.md: 'No live trading code until Phase 4'). "
            "IBKRAdapter is a structural placeholder — fill this in when Phase 4 starts, including "
            "the live_orders table / fill-polling design from SIGNAL_ALPHA_DESIGN.md §9."
        )
