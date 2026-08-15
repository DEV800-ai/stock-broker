from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.config import settings
from broker.db import check_db, get_db
from broker.models.scan import ScanRun

router = APIRouter()

MARKET_DATA_FRESHNESS = timedelta(hours=24)


class HealthResponse(BaseModel):
    status: str
    db: bool
    market_data: bool
    ai: bool


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    db_ok = check_db()
    market_data_ok = _check_market_data(db)
    ai_ok = bool(settings.openai_api_key)

    overall = "ok" if all([db_ok, ai_ok]) else "degraded"
    return HealthResponse(status=overall, db=db_ok, market_data=market_data_ok, ai=ai_ok)


def _check_market_data(db: Session) -> bool:
    last_run = db.scalar(
        select(ScanRun)
        .where(ScanRun.status == "complete")
        .order_by(desc(ScanRun.finished_at))
        .limit(1)
    )
    if last_run is None or last_run.finished_at is None:
        return False
    return datetime.utcnow() - last_run.finished_at < MARKET_DATA_FRESHNESS
