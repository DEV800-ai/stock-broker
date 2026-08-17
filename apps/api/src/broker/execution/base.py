"""Broker execution interface.

orders/service.py talks to this interface, never to a concrete adapter
directly. `PaperAdapter` (execution/paper_adapter.py) is the only adapter in
use — live execution is not planned; non-paper trades go through the manual
TradingView self-report flow (manual_execution/service.py) instead.
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
