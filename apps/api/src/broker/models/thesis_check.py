from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class ThesisCheck(Base):
    __tablename__ = "thesis_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    thesis_id: Mapped[int] = mapped_column(Integer, ForeignKey("stock_theses.id"), nullable=False)
    new_thesis_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stock_theses.id"))
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)  # daily_sweep|manual
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    changed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
