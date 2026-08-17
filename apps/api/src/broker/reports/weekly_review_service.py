import json
from dataclasses import asdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.models.performance_review import PerformanceReview
from broker.reports.paper_trading_health import build_paper_trading_health_report


def _json_safe(data: dict) -> dict:
    """Round-trip through json.dumps(default=str) so datetimes serialize to ISO strings
    before hitting the JSONB column — asdict() leaves datetime objects intact."""
    return json.loads(json.dumps(data, default=str))


def generate_weekly_review(
    db: Session, triggered_by: str, period_end: date | None = None
) -> PerformanceReview:
    """Generate (or return the existing) weekly review for the 7 days ending period_end.

    Idempotent per period_start, mirroring the thesis-caching convention of not
    regenerating the same thing twice — a second call for the same week returns
    the row already persisted instead of creating a duplicate.
    """
    period_end = period_end or date.today()
    period_start = period_end - timedelta(days=7)

    existing = db.scalars(
        select(PerformanceReview).where(PerformanceReview.period_start == period_start)
    ).first()
    if existing is not None:
        return existing

    report = build_paper_trading_health_report(db, since=period_start, until=period_end)
    report_dict = _json_safe(
        {**asdict(report), "by_source": {k: asdict(v) for k, v in report.by_source.items()}}
    )

    review = PerformanceReview(
        period_start=period_start,
        period_end=period_end,
        triggered_by=triggered_by,
        report_json=report_dict,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
