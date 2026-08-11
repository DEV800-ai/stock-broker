"""Kill switch / autonomy mode control.

AgentControl.is_killed and autonomy_mode already gate the risk engine
(risk/rules.py::check_autonomy_mode, orders/service.py::build_risk_context)
but until this module, nothing let anyone set them except a direct DB edit —
there was no API path to trip the kill switch. Every change here is
audit-logged the same way order approval is.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.audit.service import log as audit_log
from broker.models.risk import AgentControl

AUTONOMY_MODES = ("research_only", "paper_only", "preview_required")


def get_or_create_control(db: Session) -> AgentControl:
    control = db.scalars(select(AgentControl).where(AgentControl.scope == "global")).first()
    if control is None:
        control = AgentControl(scope="global")
        db.add(control)
        db.flush()
    return control


def kill(db: Session, actor: str, reason: str) -> AgentControl:
    control = get_or_create_control(db)
    control.is_killed = True
    control.killed_reason = reason
    control.killed_at = datetime.utcnow()
    control.updated_by = actor
    audit_log(db, actor=actor, action="agent_kill", entity_type="agent_control", entity_id=control.id,
              details={"reason": reason})
    db.commit()
    db.refresh(control)
    return control


def unkill(db: Session, actor: str) -> AgentControl:
    control = get_or_create_control(db)
    control.is_killed = False
    control.killed_reason = None
    control.killed_at = None
    control.updated_by = actor
    audit_log(db, actor=actor, action="agent_unkill", entity_type="agent_control", entity_id=control.id, details=None)
    db.commit()
    db.refresh(control)
    return control


class InvalidAutonomyMode(Exception):
    pass


def set_autonomy_mode(db: Session, actor: str, mode: str) -> AgentControl:
    if mode not in AUTONOMY_MODES:
        raise InvalidAutonomyMode(f"mode must be one of {AUTONOMY_MODES}, got {mode!r}")
    control = get_or_create_control(db)
    previous_mode = control.autonomy_mode
    control.autonomy_mode = mode
    control.updated_by = actor
    audit_log(db, actor=actor, action="agent_autonomy_mode_change", entity_type="agent_control",
              entity_id=control.id, details={"from": previous_mode, "to": mode})
    db.commit()
    db.refresh(control)
    return control
