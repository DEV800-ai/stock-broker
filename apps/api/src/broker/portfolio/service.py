"""Read-only portfolio view, derived entirely from PaperTrade rows.

There is no live broker connection (see docs/SIGNAL_ALPHA_DESIGN.md §9) — both
simulated paper fills and self-reported manual TradingView trades share the
same PaperTrade lifecycle, so this is the single source of truth for "what's
currently held." Aggregates reuse orders/service.py::build_portfolio_state();
this module adds the per-position detail that endpoint doesn't need.
"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.data.pricing import latest_price
from broker.models.paper_trade import PaperTrade
from broker.orders.service import build_portfolio_state


@dataclass
class Position:
    ticker: str
    shares: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    source: str


@dataclass
class PortfolioView:
    net_liquidation: float
    cash: float
    sector_values: dict[str, float]
    realized_pnl_today: float
    realized_pnl_week: float
    positions: list[Position] = field(default_factory=list)


def _enrich_position(trade: PaperTrade, current_price: float | None) -> Position:
    entry_price = trade.entry_price or 0.0
    shares = trade.shares or 0
    price = current_price if current_price is not None else entry_price
    unrealized_pnl = (price - entry_price) * shares
    unrealized_pnl_pct = (price - entry_price) / entry_price if entry_price else 0.0
    return Position(
        ticker=trade.ticker,
        shares=shares,
        entry_price=entry_price,
        current_price=price,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        source=trade.source,
    )


def get_portfolio_view(db: Session) -> PortfolioView:
    state = build_portfolio_state(db)
    open_trades = db.scalars(select(PaperTrade).where(PaperTrade.status == "open")).all()
    positions = [_enrich_position(t, latest_price(db, t.ticker)) for t in open_trades]
    return PortfolioView(
        net_liquidation=state.net_liquidation,
        cash=state.cash,
        sector_values=state.sector_values,
        realized_pnl_today=state.realized_pnl_today,
        realized_pnl_week=state.realized_pnl_week,
        positions=positions,
    )
