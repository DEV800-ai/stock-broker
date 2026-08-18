from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from broker.config import settings
from broker.db import get_db
from broker.models.scan import ScanResult, ScanRun
from broker.models.watchlist import WatchlistEntry
from broker.orders import service as orders_service

router = APIRouter()


class TradingViewLinkOut(BaseModel):
    url: str


class ScanRunOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    tickers_scanned: int | None
    tickers_flagged: int | None
    phase: str | None
    total_tickers: int | None
    tickers_processed: int | None

    model_config = {"from_attributes": True}


class ScanResultOut(BaseModel):
    id: int
    ticker: str
    scan_date: date
    composite_score: float | None
    volume_score: float | None
    momentum_score: float | None
    rs_score: float | None
    gap_score: float | None
    price: float | None
    volume_ratio: float | None
    pct_change_1d: float | None
    pct_change_5d: float | None
    rsi_14: float | None
    signals_fired: dict | None

    model_config = {"from_attributes": True}


@router.get("/scanner/runs", response_model=list[ScanRunOut])
def list_scan_runs(limit: int = 20, db: Session = Depends(get_db)) -> list[ScanRun]:
    return list(db.scalars(select(ScanRun).order_by(desc(ScanRun.started_at)).limit(limit)))


@router.get("/scanner/runs/{run_id}", response_model=ScanRunOut)
def get_scan_run(run_id: int, db: Session = Depends(get_db)) -> ScanRun:
    run = db.get(ScanRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return run


@router.delete("/scanner/runs/{run_id}", status_code=204)
def delete_scan_run(run_id: int, db: Session = Depends(get_db)) -> None:
    run = db.get(ScanRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")
    if run.status == "complete":
        raise HTTPException(status_code=400, detail="Cannot delete a completed scan run")
    if run.status == "running":
        stale_after = timedelta(minutes=settings.scan_stale_after_minutes)
        if datetime.utcnow() - run.started_at < stale_after:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Scan run is still active (running < {settings.scan_stale_after_minutes}m); "
                    "deleting it now would crash the in-progress scan. Wait for it to finish or "
                    "become stale before clearing."
                ),
            )

    result_ids = list(db.scalars(select(ScanResult.id).where(ScanResult.run_id == run_id)))
    if result_ids:
        db.query(WatchlistEntry).filter(WatchlistEntry.scan_result_id.in_(result_ids)).update(
            {"scan_result_id": None}, synchronize_session=False
        )
        db.query(ScanResult).filter(ScanResult.id.in_(result_ids)).delete(synchronize_session=False)
    db.delete(run)
    db.commit()


@router.get("/scanner/results", response_model=list[ScanResultOut])
def list_scan_results(
    scan_date: date | None = None,
    sector: str | None = None,
    min_score: float = Query(default=0.0),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
) -> list[ScanResult]:
    effective_date = scan_date
    if effective_date is None:
        effective_date = db.scalar(select(func.max(ScanResult.scan_date)))

    # A scan can be re-triggered on the same day, leaving multiple rows per
    # ticker for the same scan_date. Keep only the latest (highest id) row
    # per ticker so re-runs don't surface as duplicate cards in Top Ideas.
    latest_ids = select(func.max(ScanResult.id)).group_by(ScanResult.ticker)
    if effective_date:
        latest_ids = latest_ids.where(ScanResult.scan_date == effective_date)

    stmt = (
        select(ScanResult)
        .where(ScanResult.id.in_(latest_ids))
        .where(ScanResult.composite_score >= min_score)
        .order_by(desc(ScanResult.composite_score))
        .limit(limit)
    )
    return list(db.scalars(stmt))


@router.get("/scanner/results/{ticker}", response_model=ScanResultOut)
def get_latest_scan_result(ticker: str, db: Session = Depends(get_db)) -> ScanResult:
    result = db.scalars(
        select(ScanResult)
        .where(ScanResult.ticker == ticker.upper())
        .order_by(desc(ScanResult.scan_date), desc(ScanResult.id))
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail=f"No scan result for {ticker}")
    return result


@router.get("/scanner/results/{ticker}/tradingview", response_model=TradingViewLinkOut)
def get_tradingview_link(ticker: str, db: Session = Depends(get_db)) -> dict:
    return {"url": orders_service.tradingview_url(db, ticker.upper())}


@router.post("/scanner/trigger", status_code=202)
def trigger_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    from broker.scanner.runner import ScanRunner
    runner = ScanRunner(db)
    background_tasks.add_task(runner.run_full_scan)
    return {"message": "Scan triggered"}
