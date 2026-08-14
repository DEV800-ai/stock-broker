from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from broker.auth import require_human_actor
from broker.db import get_db
from broker.manual_execution import service

router = APIRouter()


class RecordOutcomeRequest(BaseModel):
    outcome: str  # executed|executed_with_changes|rejected|watch_only|paper_tracked|cancelled
    actual_price: float | None = None
    actual_quantity: int | None = None
    actual_order_type: str | None = None
    notes: str | None = None


class RecordOutcomeOut(BaseModel):
    id: int
    ticker: str
    status: str
    execution_mode: str
    paper_trade_id: int | None

    model_config = {"from_attributes": True}


@router.post("/manual-execution/{preview_id}", response_model=RecordOutcomeOut)
def record_outcome(
    preview_id: int,
    body: RecordOutcomeRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_human_actor),
) -> service.OrderPreview:
    try:
        return service.record_outcome(
            db,
            preview_id=preview_id,
            actor=actor,
            outcome=body.outcome,
            actual_price=body.actual_price,
            actual_quantity=body.actual_quantity,
            actual_order_type=body.actual_order_type,
            notes=body.notes,
        )
    except service.OrderPreviewNotFound as exc:
        raise HTTPException(status_code=404, detail="Order preview not found") from exc
    except (service.InvalidPreviewState, service.InvalidOutcome) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
