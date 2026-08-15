import requests
from fastapi import APIRouter
from pydantic import BaseModel

from broker.config import settings
from broker.db import check_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: bool
    ibkr_gateway: bool
    ai: bool


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = check_db()
    ibkr_ok = _check_ibkr()
    ai_ok = bool(settings.openai_api_key)

    overall = "ok" if all([db_ok, ai_ok]) else "degraded"
    return HealthResponse(status=overall, db=db_ok, ibkr_gateway=ibkr_ok, ai=ai_ok)


def _check_ibkr() -> bool:
    try:
        resp = requests.get(
            f"{settings.ibkr_gateway_url}/v1/api/iserver/auth/status", timeout=3, verify=False
        )
        return resp.status_code == 200 and resp.json().get("authenticated") is True
    except Exception:
        return False
