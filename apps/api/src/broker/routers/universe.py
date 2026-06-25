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
    with_conid: int
    tickers_with_bars: int


@router.get("/universe", response_model=UniverseStats)
def get_universe_stats(db: Session = Depends(get_db)) -> UniverseStats:
    total = db.scalar(select(func.count()).select_from(StockUniverse)) or 0
    active = db.scalar(select(func.count()).select_from(StockUniverse).where(StockUniverse.active == True)) or 0
    with_conid = db.scalar(
        select(func.count()).select_from(StockUniverse).where(StockUniverse.ibkr_conid != None)
    ) or 0
    tickers_with_bars = db.scalar(
        select(func.count(func.distinct(PriceBar.ticker))).select_from(PriceBar)
    ) or 0
    return UniverseStats(total=total, active=active, with_conid=with_conid, tickers_with_bars=tickers_with_bars)
