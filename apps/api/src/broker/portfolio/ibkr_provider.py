"""Read-only sync of the real IBKR account (positions, cash, net liquidation).

Deliberately NOT wired into orders/service.py::build_portfolio_state(), which
stays paper-trade-based and is what risk sizing actually uses. Phase 3 paper
trading is meant to stay virtual (CLAUDE.md: "No live trading code until
Phase 4") — mixing real account dollars into paper risk sizing now would
blur that line without a corresponding Phase 4 decision to trade live. This
module exists so Phase 4 has a ready-built, already-tested read path for real
account state; something will need to call get_snapshot() and feed it into
build_portfolio_state() (or a live equivalent) at that point, but that wiring
is out of scope here.

Requires the IBKR Gateway to be running and authenticated locally — see
data/ibkr.py and CLAUDE.md. get_snapshot() returns snapshot=None (not a
partial/fabricated snapshot) if the gateway is unreachable or has no linked
account, so callers can't silently treat missing data as zero.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from broker.data.ibkr import IBKRClient


@dataclass
class PortfolioSnapshot:
    account_id: str
    net_liquidation: float
    cash: float
    position_values: dict[str, float] = field(default_factory=dict)
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, max_age_seconds: float) -> bool:
        age = (datetime.now(timezone.utc) - self.as_of).total_seconds()
        return age > max_age_seconds


class IBKRPortfolioProvider:
    """Wraps IBKRClient to assemble a single point-in-time PortfolioSnapshot."""

    def __init__(self, client: IBKRClient | None = None) -> None:
        self._client = client or IBKRClient()

    def get_snapshot(self) -> PortfolioSnapshot | None:
        if not self._client.is_authenticated():
            return None

        accounts = self._client.get_accounts()
        if not accounts:
            return None
        account_id = accounts[0].get("accountId") or accounts[0].get("id")
        if not account_id:
            return None

        ledger = self._client.get_ledger(account_id)
        base = ledger.get("BASE", {}) if isinstance(ledger, dict) else {}
        net_liquidation = base.get("netliquidationvalue")
        cash = base.get("cashbalance")
        if net_liquidation is None or cash is None:
            return None

        positions = self._client.get_positions(account_id)
        position_values = {
            p["ticker"]: p.get("mktValue", 0.0)
            for p in positions
            if p.get("ticker")
        }

        return PortfolioSnapshot(
            account_id=account_id,
            net_liquidation=float(net_liquidation),
            cash=float(cash),
            position_values=position_values,
        )
