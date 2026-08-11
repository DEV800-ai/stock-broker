from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.audit.service import verify_chain
from broker.db import get_db
from broker.models.audit import AuditLog

router = APIRouter()


class AuditChainVerificationOut(BaseModel):
    ok: bool
    checked: int
    broken_at_id: int | None
    reason: str | None


@router.get("/audit/verify", response_model=AuditChainVerificationOut)
def verify_audit_chain(db: Session = Depends(get_db)) -> AuditChainVerificationOut:
    result = verify_chain(db)
    return AuditChainVerificationOut(
        ok=result.ok, checked=result.checked, broken_at_id=result.broken_at_id, reason=result.reason
    )


class AuditLogOut(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str | None
    entity_id: int | None
    details_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/audit", response_model=list[AuditLogOut])
def list_audit_log(
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    return list(db.scalars(stmt))
