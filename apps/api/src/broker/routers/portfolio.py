from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.portfolio.service import get_portfolio_view

router = APIRouter()


class PositionOut(BaseModel):
    ticker: str
    shares: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    source: str


class PortfolioOut(BaseModel):
    net_liquidation: float
    cash: float
    sector_values: dict[str, float]
    realized_pnl_today: float
    realized_pnl_week: float
    positions: list[PositionOut]


@router.get("/portfolio", response_model=PortfolioOut)
def get_portfolio(db: Session = Depends(get_db)) -> PortfolioOut:
    view = get_portfolio_view(db)
    return PortfolioOut(
        net_liquidation=view.net_liquidation,
        cash=view.cash,
        sector_values=view.sector_values,
        realized_pnl_today=view.realized_pnl_today,
        realized_pnl_week=view.realized_pnl_week,
        positions=[PositionOut(**vars(p)) for p in view.positions],
    )
