from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class StockThesis(Base):
    __tablename__ = "stock_theses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    scan_result_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_results.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    model: Mapped[str | None] = mapped_column(String(100))

    why_interesting: Mapped[str] = mapped_column(Text, nullable=False)
    risk_factors: Mapped[str] = mapped_column(Text, nullable=False)
    sector_context: Mapped[str | None] = mapped_column(Text)
    peer_comparison: Mapped[str | None] = mapped_column(Text)
    news_summary: Mapped[str | None] = mapped_column(Text)
    catalysts: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(20))  # high|medium|low

    news_score: Mapped[float | None] = mapped_column(Double)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(12), index=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    input_json: Mapped[dict | None] = mapped_column(JSONB)
    output_json: Mapped[dict | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
