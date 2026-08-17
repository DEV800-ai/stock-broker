from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.models.performance_review import PerformanceReview
from broker.reports.paper_trading_health import build_paper_trading_health_report
from broker.reports.weekly_review_service import generate_weekly_review

router = APIRouter()


class SourceBreakdownOut(BaseModel):
    trade_count: int
    trade_status_counts: dict[str, int]
    closed_trade_count: int
    win_count: int
    win_rate: float | None
    avg_pnl_pct: float | None
    outcome_counts: dict[str, int]


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
    trade_source_counts: dict[str, int]
    by_source: dict[str, SourceBreakdownOut]
    closed_trade_count: int
    win_count: int
    win_rate: float | None
    avg_pnl_pct: float | None
    avg_entry_slippage_pct: float | None


class PerformanceReviewOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    generated_at: datetime
    triggered_by: str
    report: PaperTradingHealthOut

    @classmethod
    def from_model(cls, review: PerformanceReview) -> "PerformanceReviewOut":
        return cls(
            id=review.id,
            period_start=review.period_start,
            period_end=review.period_end,
            generated_at=review.generated_at,
            triggered_by=review.triggered_by,
            report=PaperTradingHealthOut(**review.report_json),
        )


@router.get("/reports/paper-trading-health", response_model=PaperTradingHealthOut)
def paper_trading_health(since: date | None = None, db: Session = Depends(get_db)) -> PaperTradingHealthOut:
    report = build_paper_trading_health_report(db, since=since)
    data = {**report.__dict__, "by_source": {k: v.__dict__ for k, v in report.by_source.items()}}
    return PaperTradingHealthOut(**data)


@router.post("/reports/weekly-review/generate", response_model=PerformanceReviewOut, status_code=202)
def trigger_weekly_review(db: Session = Depends(get_db)) -> PerformanceReviewOut:
    review = generate_weekly_review(db, triggered_by="manual")
    return PerformanceReviewOut.from_model(review)


@router.get("/reports/weekly-review", response_model=list[PerformanceReviewOut])
def list_weekly_reviews(limit: int = 12, db: Session = Depends(get_db)) -> list[PerformanceReviewOut]:
    reviews = db.scalars(
        select(PerformanceReview).order_by(desc(PerformanceReview.period_start)).limit(limit)
    ).all()
    return [PerformanceReviewOut.from_model(r) for r in reviews]


@router.get("/reports/weekly-review/latest", response_model=PerformanceReviewOut)
def latest_weekly_review(db: Session = Depends(get_db)) -> PerformanceReviewOut:
    review = db.scalars(
        select(PerformanceReview).order_by(desc(PerformanceReview.period_start)).limit(1)
    ).first()
    if review is None:
        raise HTTPException(status_code=404, detail="No weekly review has been generated yet")
    return PerformanceReviewOut.from_model(review)
