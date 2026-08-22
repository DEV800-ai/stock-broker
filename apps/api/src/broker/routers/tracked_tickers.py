import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.auth import require_actor
from broker.db import get_db
from broker.models.scan import ScanResult
from broker.models.tracked_ticker import TrackedTicker

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")


class TrackedTickerOut(BaseModel):
    id: int
    ticker: str
    notes: str | None
    created_at: datetime
    latest_price: float | None = None
    latest_composite_score: float | None = None


class AddTrackedTickerRequest(BaseModel):
    ticker: str
    notes: str | None = None


def _latest_scan(db: Session, ticker: str) -> ScanResult | None:
    return db.scalars(
        select(ScanResult)
        .where(ScanResult.ticker == ticker)
        .order_by(desc(ScanResult.scan_date), desc(ScanResult.id))
    ).first()


@router.get("/tracked-tickers", response_model=list[TrackedTickerOut])
def list_tracked_tickers(
    db: Session = Depends(get_db), actor: str = Depends(require_actor)
) -> list[TrackedTickerOut]:
    rows = db.scalars(
        select(TrackedTicker).where(TrackedTicker.actor == actor).order_by(desc(TrackedTicker.created_at))
    )
    out = []
    for row in rows:
        latest = _latest_scan(db, row.ticker)
        out.append(
            TrackedTickerOut(
                id=row.id,
                ticker=row.ticker,
                notes=row.notes,
                created_at=row.created_at,
                latest_price=latest.price if latest else None,
                latest_composite_score=latest.composite_score if latest else None,
            )
        )
    return out


@router.post("/tracked-tickers", response_model=TrackedTickerOut, status_code=201)
def add_tracked_ticker(
    body: AddTrackedTickerRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_actor),
) -> TrackedTickerOut:
    ticker = body.ticker.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    existing = db.scalars(
        select(TrackedTicker).where(TrackedTicker.actor == actor, TrackedTicker.ticker == ticker)
    ).first()
    if existing:
        latest = _latest_scan(db, existing.ticker)
        return TrackedTickerOut(
            id=existing.id,
            ticker=existing.ticker,
            notes=existing.notes,
            created_at=existing.created_at,
            latest_price=latest.price if latest else None,
            latest_composite_score=latest.composite_score if latest else None,
        )

    row = TrackedTicker(actor=actor, ticker=ticker, notes=body.notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    latest = _latest_scan(db, row.ticker)
    return TrackedTickerOut(
        id=row.id,
        ticker=row.ticker,
        notes=row.notes,
        created_at=row.created_at,
        latest_price=latest.price if latest else None,
        latest_composite_score=latest.composite_score if latest else None,
    )


@router.delete("/tracked-tickers/{ticker}", status_code=204)
def remove_tracked_ticker(
    ticker: str, db: Session = Depends(get_db), actor: str = Depends(require_actor)
) -> None:
    row = db.scalars(
        select(TrackedTicker).where(TrackedTicker.actor == actor, TrackedTicker.ticker == ticker.upper())
    ).first()
    if row:
        db.delete(row)
        db.commit()
