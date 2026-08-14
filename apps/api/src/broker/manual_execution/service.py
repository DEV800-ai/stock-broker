"""Records what a human actually did after being sent to TradingView to manually
trade an approved order preview. Signal Alpha has no way to observe this directly —
see docs/SIGNAL_ALPHA_TRADINGVIEW_MVP_DRAFT.md §21 — so this is entirely self-reported,
once, per preview.
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from broker.audit.service import log as audit_log
from broker.models.order import OrderPreview
from broker.models.paper_trade import PaperTrade

OUTCOMES = (
    "executed",
    "executed_with_changes",
    "rejected",
    "watch_only",
    "paper_tracked",
    "cancelled",
)

# Outcomes that mean the user actually holds a position now.
_POSITION_OUTCOMES = ("executed", "executed_with_changes")


class OrderPreviewNotFound(Exception):
    pass


class InvalidPreviewState(Exception):
    pass


class InvalidOutcome(Exception):
    pass


def record_outcome(
    db: Session,
    preview_id: int,
    actor: str,
    outcome: str,
    actual_price: float | None = None,
    actual_quantity: int | None = None,
    actual_order_type: str | None = None,
    notes: str | None = None,
) -> OrderPreview:
    if outcome not in OUTCOMES:
        raise InvalidOutcome(f"outcome must be one of {OUTCOMES}, got {outcome!r}")

    preview = db.get(OrderPreview, preview_id)
    if not preview:
        raise OrderPreviewNotFound(preview_id)
    if preview.execution_mode != "manual_tradingview":
        raise InvalidPreviewState(
            f"Order preview {preview_id} has execution_mode {preview.execution_mode!r}, not manual_tradingview"
        )
    if preview.status != "approved":
        raise InvalidPreviewState(f"Order preview {preview_id} is {preview.status}, not approved")

    trade: PaperTrade | None = None
    if outcome in _POSITION_OUTCOMES:
        trade = PaperTrade(
            ticker=preview.ticker,
            thesis_id=preview.thesis_id,
            entry_price=actual_price if actual_price is not None else preview.limit_price,
            shares=actual_quantity if actual_quantity is not None else preview.shares,
            requested_shares=preview.shares,
            status="open",
            entry_date=date.today(),
            approved_by=actor,
            approved_at=datetime.utcnow(),
            source="manual_tradingview",
            reported_by=actor,
            outcome=outcome,
            execution_notes=notes,
            notes=f"Manually executed from order_preview {preview.id}: {preview.reason}",
        )
        db.add(trade)
        db.flush()
        preview.paper_trade_id = trade.id

    preview.status = "manual_recorded"
    audit_log(
        db, actor=actor, action="manual_execution_recorded", entity_type="order_preview", entity_id=preview.id,
        details={
            "ticker": preview.ticker,
            "outcome": outcome,
            "actual_price": actual_price,
            "actual_quantity": actual_quantity,
            "actual_order_type": actual_order_type,
            "paper_trade_id": trade.id if trade else None,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview
