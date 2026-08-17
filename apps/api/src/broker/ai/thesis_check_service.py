import logging
from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from broker.ai.thesis_agent import ThesisAgent
from broker.config import settings
from broker.models.thesis import StockThesis
from broker.models.thesis_check import ThesisCheck
from broker.models.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)


def _has_meaningfully_changed(old: StockThesis, new: StockThesis) -> bool:
    if old.confidence != new.confidence:
        return True
    if old.news_score is not None and new.news_score is not None:
        if abs(new.news_score - old.news_score) >= 0.2:
            return True
    return False


def _latest_thesis(db: Session, ticker: str) -> StockThesis | None:
    return db.scalars(
        select(StockThesis)
        .where(StockThesis.ticker == ticker)
        .order_by(desc(StockThesis.generated_at))
    ).first()


def recheck_ticker(db: Session, ticker: str, triggered_by: str) -> ThesisCheck:
    """Force-regenerate a ticker's thesis and record what, if anything, changed."""
    ticker = ticker.upper()
    old_thesis = _latest_thesis(db, ticker)
    if old_thesis is None:
        raise ValueError(f"No existing thesis for {ticker} to re-check")

    check = ThesisCheck(ticker=ticker, thesis_id=old_thesis.id, triggered_by=triggered_by, changed=False)

    try:
        new_thesis = ThesisAgent(db).generate(ticker, force_refresh=True)
    except Exception as exc:
        check.notes = f"recheck failed: {exc}"
        db.add(check)
        db.commit()
        logger.warning("Thesis recheck failed for %s: %s", ticker, exc)
        return check

    check.new_thesis_id = new_thesis.id
    check.changed = _has_meaningfully_changed(old_thesis, new_thesis)
    db.add(check)
    db.commit()
    return check


def sweep_stale_theses(db: Session, max_age_hours: int | None = None) -> list[ThesisCheck]:
    """Re-check every actively-watched ticker whose thesis is older than max_age_hours."""
    if max_age_hours is None:
        max_age_hours = settings.thesis_recheck_max_age_hours
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

    latest_date = db.scalar(select(func.max(WatchlistEntry.watchlist_date)))
    if latest_date is None:
        return []

    tickers = db.scalars(
        select(WatchlistEntry.ticker)
        .where(WatchlistEntry.watchlist_date == latest_date)
        .where(WatchlistEntry.status != "avoid")
        .distinct()
    ).all()

    checks: list[ThesisCheck] = []
    for ticker in tickers:
        thesis = _latest_thesis(db, ticker)
        if thesis is None or thesis.generated_at > cutoff:
            continue
        try:
            checks.append(recheck_ticker(db, ticker, triggered_by="daily_sweep"))
        except ValueError:
            continue
    return checks
