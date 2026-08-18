from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|complete|failed
    tickers_scanned: Mapped[int | None] = mapped_column(Integer)
    tickers_flagged: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    params_json: Mapped[dict | None] = mapped_column(JSONB)


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_runs.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    scan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Composite + signal scores
    composite_score: Mapped[float | None] = mapped_column(Double)
    volume_score: Mapped[float | None] = mapped_column(Double)
    momentum_score: Mapped[float | None] = mapped_column(Double)
    rs_score: Mapped[float | None] = mapped_column(Double)
    gap_score: Mapped[float | None] = mapped_column(Double)

    # Raw market data
    price: Mapped[float | None] = mapped_column(Double)
    volume_ratio: Mapped[float | None] = mapped_column(Double)
    pct_change_1d: Mapped[float | None] = mapped_column(Double)
    pct_change_5d: Mapped[float | None] = mapped_column(Double)
    pct_change_20d: Mapped[float | None] = mapped_column(Double)
    sma20: Mapped[float | None] = mapped_column(Double)
    sma50: Mapped[float | None] = mapped_column(Double)
    sma200: Mapped[float | None] = mapped_column(Double)
    rsi_14: Mapped[float | None] = mapped_column(Double)
    macd: Mapped[float | None] = mapped_column(Double)
    macd_signal: Mapped[float | None] = mapped_column(Double)
    macd_histogram: Mapped[float | None] = mapped_column(Double)
    bb_upper: Mapped[float | None] = mapped_column(Double)
    bb_lower: Mapped[float | None] = mapped_column(Double)
    bb_percent_b: Mapped[float | None] = mapped_column(Double)
    above_sma50: Mapped[bool | None] = mapped_column(Boolean)
    above_sma200: Mapped[bool | None] = mapped_column(Boolean)
    signals_fired: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
