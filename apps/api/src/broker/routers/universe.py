from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.models.price_bar import PriceBar
from broker.models.universe import StockUniverse

router = APIRouter()


class UniverseStats(BaseModel):
    total: int
    active: int
    tickers_with_bars: int


def count_tickers_with_bars(db: Session) -> int:
    """Universe tickers that have at least one stored price bar.

    One EXISTS probe per universe row on the ix_price_bars_ticker index, rather
    than COUNT(DISTINCT ticker) over the whole price_bars table. The dashboard
    polls this endpoint, and the full-table scan got slow enough during a scan's
    bulk bar upserts to help exhaust the DB connection pool.
    """
    has_bars = select(PriceBar.id).where(PriceBar.ticker == StockUniverse.ticker).exists()
    return db.scalar(select(func.count()).select_from(StockUniverse).where(has_bars)) or 0


@router.get("/universe", response_model=UniverseStats)
def get_universe_stats(db: Session = Depends(get_db)) -> UniverseStats:
    total = db.scalar(select(func.count()).select_from(StockUniverse)) or 0
    active = db.scalar(select(func.count()).select_from(StockUniverse).where(StockUniverse.active == True)) or 0
    tickers_with_bars = count_tickers_with_bars(db)
    return UniverseStats(total=total, active=active, tickers_with_bars=tickers_with_bars)
