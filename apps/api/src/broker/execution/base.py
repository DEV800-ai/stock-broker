"""Broker execution interface.

orders/service.py talks to this interface, never to a concrete adapter or to
IBKRClient directly. That indirection is the actual safety boundary described
in SIGNAL_ALPHA_DESIGN.md §9/§16: a future developer adding live execution
has to plug a new adapter into `get_broker_adapter()`, not sprinkle
`IBKRClient.place_order()` calls through the order-approval code path.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FillResult:
    status: str  # "filled" | "partial" | "rejected"
    filled_shares: int
    fill_price: float | None  # None when rejected
    theoretical_price: float  # the old exact-limit-price model, for comparison


class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order(
        self,
        action: str,
        ticker: str,
        limit_price: float,
        requested_shares: int,
        avg_daily_volume: float | None,
        allow_partial: bool,
    ) -> FillResult:
        """Submit an order and return its fill outcome (or raise on rejection paths
        the adapter can't represent as a FillResult, e.g. a disabled live adapter)."""
