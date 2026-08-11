from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from broker.agent_control import service
from broker.auth import require_actor, require_human_actor
from broker.db import get_db

router = APIRouter()


class AgentControlOut(BaseModel):
    scope: str
    autonomy_mode: str
    is_killed: bool
    killed_reason: str | None
    killed_at: datetime | None
    updated_at: datetime
    updated_by: str | None

    model_config = {"from_attributes": True}


class KillIn(BaseModel):
    reason: str


class AutonomyModeIn(BaseModel):
    mode: str


@router.get("/agent-control", response_model=AgentControlOut)
def get_agent_control(db: Session = Depends(get_db)) -> AgentControlOut:
    return service.get_or_create_control(db)


@router.post("/agent-control/kill", response_model=AgentControlOut)
def kill_agent(
    body: KillIn, db: Session = Depends(get_db), actor: str = Depends(require_actor)
) -> AgentControlOut:
    return service.kill(db, actor=actor, reason=body.reason)


@router.post("/agent-control/unkill", response_model=AgentControlOut)
def unkill_agent(db: Session = Depends(get_db), actor: str = Depends(require_human_actor)) -> AgentControlOut:
    return service.unkill(db, actor=actor)


@router.post("/agent-control/autonomy-mode", response_model=AgentControlOut)
def set_autonomy_mode(
    body: AutonomyModeIn, db: Session = Depends(get_db), actor: str = Depends(require_human_actor)
) -> AgentControlOut:
    try:
        return service.set_autonomy_mode(db, actor=actor, mode=body.mode)
    except service.InvalidAutonomyMode as exc:
        raise HTTPException(status_code=422, detail=str(exc))
