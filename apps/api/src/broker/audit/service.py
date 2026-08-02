"""Audit log writer.

Every state-changing action in the app (order approval/rejection, paper trade
approval/rejection/close, ...) should call log() as part of the same DB
transaction as the action itself, so the audit row and the action it
describes commit or roll back together — no action is ever unaudited because
a caller forgot to commit.
"""
from sqlalchemy.orm import Session

from broker.models.audit import AuditLog


def log(
    db: Session,
    actor: str,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details,
    )
    db.add(entry)
    db.flush()
    return entry
