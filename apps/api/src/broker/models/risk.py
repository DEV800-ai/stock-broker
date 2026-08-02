from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class RiskPolicy(Base):
    __tablename__ = "risk_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    params_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RiskEvaluationRecord(Base):
    __tablename__ = "risk_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    # order_preview_id has no FK yet — order_previews table lands in a later milestone.
    order_preview_id: Mapped[int | None] = mapped_column(Integer, index=True)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rule_results_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentControl(Base):
    __tablename__ = "agent_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="global")
    # research_only|paper_only|preview_required
    autonomy_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="preview_required")
    is_killed: Mapped[bool] = mapped_column(Boolean, default=False)
    killed_reason: Mapped[str | None] = mapped_column(Text)
    killed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
