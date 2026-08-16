from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.models.watchlist import WatchlistEntry

router = APIRouter()


class WatchlistEntryOut(BaseModel):
    id: int
    ticker: str
    watchlist_date: date
    rank: int
    status: str
    composite_score: float | None
    scan_result_id: int | None
    thesis_id: int | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str


VALID_STATUSES = {"watch", "research", "paper", "avoid"}


@router.get("/watchlist", response_model=list[WatchlistEntryOut])
def get_watchlist(
    watchlist_date: date | None = None,
    status: str | None = None,
    sector: str | None = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
) -> list[WatchlistEntry]:
    effective_date = watchlist_date
    if effective_date is None:
        effective_date = db.scalar(select(func.max(WatchlistEntry.watchlist_date))) or date.today()
    stmt = (
        select(WatchlistEntry)
        .where(WatchlistEntry.watchlist_date == effective_date)
        .order_by(WatchlistEntry.rank)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(WatchlistEntry.status == status)
    return list(db.scalars(stmt))


@router.put("/watchlist/{ticker}/status", response_model=WatchlistEntryOut)
def update_watchlist_status(
    ticker: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
) -> WatchlistEntry:
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {VALID_STATUSES}")
    entry = db.scalars(
        select(WatchlistEntry)
        .where(WatchlistEntry.ticker == ticker.upper())
        .order_by(desc(WatchlistEntry.watchlist_date))
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    entry.status = body.status
    db.commit()
    db.refresh(entry)
    return entry
