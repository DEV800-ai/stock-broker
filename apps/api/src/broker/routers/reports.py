from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.reports.paper_trading_health import build_paper_trading_health_report

router = APIRouter()


class PaperTradingHealthOut(BaseModel):
    since: datetime | None
    generated_at: datetime
    earliest_activity: datetime | None
    days_of_history: float | None
    preview_count: int
    preview_status_counts: dict[str, int]
    risk_verdict_counts: dict[str, int]
    trade_count: int
    trade_status_counts: dict[str, int]
    fill_status_counts: dict[str, int]
    closed_trade_count: int
    win_count: int
    win_rate: float | None
    avg_pnl_pct: float | None
    avg_entry_slippage_pct: float | None


@router.get("/reports/paper-trading-health", response_model=PaperTradingHealthOut)
def paper_trading_health(since: date | None = None, db: Session = Depends(get_db)) -> PaperTradingHealthOut:
    report = build_paper_trading_health_report(db, since=since)
    return PaperTradingHealthOut(**report.__dict__)
