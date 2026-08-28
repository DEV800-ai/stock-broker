from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.models.thesis import StockThesis
from broker.models.thesis_check import ThesisCheck

router = APIRouter()


class ThesisOut(BaseModel):
    id: int
    ticker: str
    scan_result_id: int | None
    generated_at: datetime
    model: str | None
    why_interesting: str
    risk_factors: str
    sector_context: str | None
    peer_comparison: str | None
    elliott_wave_context: str | None
    news_summary: str | None
    catalysts: str | None
    confidence: str | None
    news_score: float | None

    model_config = {"from_attributes": True}


class GenerateThesisRequest(BaseModel):
    ticker: str
    scan_result_id: int | None = None
    force_refresh: bool = False


class ThesisCheckOut(BaseModel):
    id: int
    ticker: str
    thesis_id: int
    new_thesis_id: int | None
    triggered_by: str
    checked_at: datetime
    changed: bool
    notes: str | None

    model_config = {"from_attributes": True}


class ThesisTranslationOut(BaseModel):
    thesis_id: int
    language: str
    why_interesting: str
    risk_factors: str
    sector_context: str | None
    peer_comparison: str | None
    elliott_wave_context: str | None
    news_summary: str | None
    catalysts: str | None


@router.get("/thesis/{ticker}", response_model=ThesisOut)
def get_latest_thesis(ticker: str, db: Session = Depends(get_db)) -> StockThesis:
    thesis = db.scalars(
        select(StockThesis)
        .where(StockThesis.ticker == ticker.upper())
        .order_by(desc(StockThesis.generated_at))
    ).first()
    if not thesis:
        raise HTTPException(status_code=404, detail=f"No thesis found for {ticker}")
    return thesis


@router.get("/theses/{thesis_id}/hebrew", response_model=ThesisTranslationOut)
def get_hebrew_thesis(thesis_id: int, db: Session = Depends(get_db)) -> dict:
    from broker.ai.thesis_translation import ThesisTranslationError, translate_thesis_to_hebrew

    thesis = db.get(StockThesis, thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    try:
        return translate_thesis_to_hebrew(db, thesis).model_dump()
    except ThesisTranslationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/thesis/{ticker}/history", response_model=list[ThesisOut])
def get_thesis_history(ticker: str, db: Session = Depends(get_db)) -> list[StockThesis]:
    return list(
        db.scalars(
            select(StockThesis)
            .where(StockThesis.ticker == ticker.upper())
            .order_by(desc(StockThesis.generated_at))
            .limit(20)
        )
    )


@router.post("/thesis/generate", status_code=202)
def generate_thesis(
    body: GenerateThesisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    from broker.ai.thesis_agent import ThesisAgent
    agent = ThesisAgent(db)
    background_tasks.add_task(agent.generate, body.ticker.upper(), body.scan_result_id, body.force_refresh)
    return {"message": f"Thesis generation queued for {body.ticker.upper()}"}


@router.post("/thesis-checks/sweep", status_code=202)
def trigger_thesis_sweep(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    from broker.ai.thesis_check_service import sweep_stale_theses
    background_tasks.add_task(sweep_stale_theses, db)
    return {"message": "Thesis re-check sweep queued"}


@router.get("/thesis-checks/{ticker}", response_model=list[ThesisCheckOut])
def get_thesis_checks(ticker: str, db: Session = Depends(get_db)) -> list[ThesisCheck]:
    return list(
        db.scalars(
            select(ThesisCheck)
            .where(ThesisCheck.ticker == ticker.upper())
            .order_by(desc(ThesisCheck.checked_at))
            .limit(20)
        )
    )
