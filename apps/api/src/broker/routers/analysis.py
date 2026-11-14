import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.db import get_db
from broker.models.thesis import StockThesis

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")


class AnalysisOut(BaseModel):
    id: int
    ticker: str
    generated_at: datetime
    model: str | None
    why_interesting: str
    risk_factors: str
    sector_context: str | None
    peer_comparison: str | None
    news_summary: str | None
    catalysts: str | None
    confidence: str | None
    news_score: float | None

    model_config = {"from_attributes": True}


class GenerateAnalysisRequest(BaseModel):
    ticker: str


@router.post("/analysis/generate", status_code=202)
def generate_analysis(
    body: GenerateAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    from broker.ai.thesis_agent import ThesisAgent

    ticker = body.ticker.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    agent = ThesisAgent(db)
    background_tasks.add_task(agent.generate, ticker, None, False, adhoc=True)
    return {"message": f"Analysis queued for {ticker}"}


@router.get("/analysis/{ticker}", response_model=AnalysisOut)
def get_latest_analysis(ticker: str, db: Session = Depends(get_db)) -> StockThesis:
    thesis = db.scalars(
        select(StockThesis)
        .where(StockThesis.ticker == ticker.upper())
        .order_by(desc(StockThesis.generated_at))
    ).first()
    if not thesis:
        raise HTTPException(status_code=404, detail=f"No analysis found for {ticker}")
    return thesis
