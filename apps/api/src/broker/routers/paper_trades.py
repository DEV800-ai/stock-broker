from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.audit.service import log as audit_log
from broker.auth import require_human_actor
from broker.db import get_db
from broker.models.paper_trade import PaperTrade

router = APIRouter()


class PaperTradeOut(BaseModel):
    id: int
    ticker: str
    thesis_id: int | None
    entry_date: date | None
    entry_price: float | None
    target_price: float | None
    stop_price: float | None
    shares: int | None
    status: str
    source: str
    approved_by: str | None
    approved_at: datetime | None
    exit_price: float | None
    exit_date: date | None
    pnl: float | None
    pnl_pct: float | None
    close_reason: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreatePaperTradeRequest(BaseModel):
    ticker: str
    thesis_id: int | None = None
    entry_price: float
    target_price: float | None = None
    stop_price: float | None = None
    shares: int = 1
    notes: str | None = None


class ClosePaperTradeRequest(BaseModel):
    exit_price: float
    close_reason: str = "manual"  # target_hit|stop_hit|manual|expired


@router.get("/paper-trades", response_model=list[PaperTradeOut])
def list_paper_trades(db: Session = Depends(get_db)) -> list[PaperTrade]:
    return list(db.scalars(select(PaperTrade).order_by(PaperTrade.created_at.desc())))


@router.post("/paper-trades", response_model=PaperTradeOut, status_code=201)
def create_paper_trade(body: CreatePaperTradeRequest, db: Session = Depends(get_db)) -> PaperTrade:
    trade = PaperTrade(
        ticker=body.ticker.upper(),
        thesis_id=body.thesis_id,
        entry_price=body.entry_price,
        target_price=body.target_price,
        stop_price=body.stop_price,
        shares=body.shares,
        status="pending_approval",
        notes=body.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.put("/paper-trades/{trade_id}/approve", response_model=PaperTradeOut)
def approve_paper_trade(
    trade_id: int, db: Session = Depends(get_db), actor: str = Depends(require_human_actor)
) -> PaperTrade:
    trade = db.get(PaperTrade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Trade is already {trade.status}")
    trade.status = "open"
    trade.entry_date = date.today()
    trade.approved_by = actor
    trade.approved_at = datetime.utcnow()
    audit_log(
        db, actor=actor, action="approve_paper_trade", entity_type="paper_trade", entity_id=trade.id,
        details={"ticker": trade.ticker, "entry_price": trade.entry_price, "shares": trade.shares},
    )
    db.commit()
    db.refresh(trade)
    return trade


@router.put("/paper-trades/{trade_id}/reject", response_model=PaperTradeOut)
def reject_paper_trade(
    trade_id: int, db: Session = Depends(get_db), actor: str = Depends(require_human_actor)
) -> PaperTrade:
    trade = db.get(PaperTrade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.status = "rejected"
    audit_log(
        db, actor=actor, action="reject_paper_trade", entity_type="paper_trade", entity_id=trade.id,
        details={"ticker": trade.ticker},
    )
    db.commit()
    db.refresh(trade)
    return trade


@router.put("/paper-trades/{trade_id}/close", response_model=PaperTradeOut)
def close_paper_trade(
    trade_id: int,
    body: ClosePaperTradeRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_human_actor),
) -> PaperTrade:
    trade = db.get(PaperTrade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail=f"Trade is {trade.status}, not open")
    trade.status = "closed"
    trade.exit_price = body.exit_price
    trade.exit_date = date.today()
    trade.close_reason = body.close_reason
    if trade.entry_price and trade.shares:
        trade.pnl = (body.exit_price - trade.entry_price) * trade.shares
        trade.pnl_pct = (body.exit_price - trade.entry_price) / trade.entry_price
    if trade.entry_date:
        trade.hold_days = (date.today() - trade.entry_date).days
    audit_log(
        db, actor=actor, action="close_paper_trade", entity_type="paper_trade", entity_id=trade.id,
        details={"ticker": trade.ticker, "exit_price": trade.exit_price, "pnl": trade.pnl, "close_reason": trade.close_reason},
    )
    db.commit()
    db.refresh(trade)
    return trade
