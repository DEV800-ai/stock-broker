from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.auth import require_actor
from broker.db import get_db
from broker.models.order import OrderPreview
from broker.orders import service

router = APIRouter()


class OrderPreviewOut(BaseModel):
    id: int
    ticker: str
    thesis_id: int | None
    action: str
    shares: int
    order_type: str
    limit_price: float
    time_in_force: str
    reason: str
    bull_case: str | None
    bear_case: str | None
    portfolio_impact: str | None
    risk_status: str
    approval_required: bool
    status: str
    paper_trade_id: int | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderPreviewDetailOut(OrderPreviewOut):
    risk_results: list[dict] | None = None


class CreateOrderPreviewRequest(BaseModel):
    ticker: str
    action: str  # BUY|SELL
    reason: str
    thesis_id: int | None = None
    shares: int | None = None
    amount_usd: float | None = None
    limit_price: float | None = None
    order_type: str = "LIMIT"
    time_in_force: str = "DAY"


@router.post("/orders/preview", response_model=OrderPreviewDetailOut, status_code=201)
def preview_order(body: CreateOrderPreviewRequest, db: Session = Depends(get_db)) -> dict:
    try:
        preview = service.create_preview(
            db,
            ticker=body.ticker,
            action=body.action,
            reason=body.reason,
            thesis_id=body.thesis_id,
            shares=body.shares,
            amount_usd=body.amount_usd,
            limit_price=body.limit_price,
            order_type=body.order_type,
            time_in_force=body.time_in_force,
        )
    except service.InvalidOrderRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        **OrderPreviewOut.model_validate(preview).model_dump(),
        "risk_results": service.get_risk_results(db, preview.id),
    }


@router.get("/orders/queue", response_model=list[OrderPreviewOut])
def list_queue(db: Session = Depends(get_db)) -> list[OrderPreview]:
    return list(
        db.scalars(
            select(OrderPreview).where(OrderPreview.status == "pending").order_by(OrderPreview.created_at)
        )
    )


@router.get("/orders/{preview_id}", response_model=OrderPreviewDetailOut)
def get_order_preview(preview_id: int, db: Session = Depends(get_db)) -> dict:
    preview = db.get(OrderPreview, preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Order preview not found")
    return {
        **OrderPreviewOut.model_validate(preview).model_dump(),
        "risk_results": service.get_risk_results(db, preview_id),
    }


@router.post("/orders/{preview_id}/approve", response_model=OrderPreviewOut)
def approve_order(
    preview_id: int, db: Session = Depends(get_db), actor: str = Depends(require_actor)
) -> OrderPreview:
    try:
        return service.approve_preview(db, preview_id, approved_by=actor)
    except service.OrderPreviewNotFound as exc:
        raise HTTPException(status_code=404, detail="Order preview not found") from exc
    except service.InvalidPreviewState as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except service.PreviewExpired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except service.PreviewBlockedAtApproval as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except service.FillRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{preview_id}/reject", response_model=OrderPreviewOut)
def reject_order(
    preview_id: int, db: Session = Depends(get_db), actor: str = Depends(require_actor)
) -> OrderPreview:
    try:
        return service.reject_preview(db, preview_id, rejected_by=actor)
    except service.OrderPreviewNotFound as exc:
        raise HTTPException(status_code=404, detail="Order preview not found") from exc
    except service.InvalidPreviewState as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
