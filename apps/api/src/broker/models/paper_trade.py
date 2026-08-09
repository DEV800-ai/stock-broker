from datetime import date, datetime

from sqlalchemy import Date, DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    thesis_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stock_theses.id"))

    entry_date: Mapped[date | None] = mapped_column(Date)
    entry_price: Mapped[float | None] = mapped_column(Double)
    target_price: Mapped[float | None] = mapped_column(Double)
    stop_price: Mapped[float | None] = mapped_column(Double)
    shares: Mapped[int | None] = mapped_column(Integer)

    # Requested vs. actually-filled size/price, so theoretical (naive) performance
    # can be compared against what the fill simulator actually executed. See
    # execution/paper_adapter.py.
    requested_shares: Mapped[int | None] = mapped_column(Integer)
    theoretical_entry_price: Mapped[float | None] = mapped_column(Double)
    theoretical_exit_price: Mapped[float | None] = mapped_column(Double)
    fill_status: Mapped[str | None] = mapped_column(String(20))  # filled|partial

    # pending_approval → open → closed / rejected
    status: Mapped[str] = mapped_column(String(20), default="pending_approval", index=True)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    exit_date: Mapped[date | None] = mapped_column(Date)
    exit_price: Mapped[float | None] = mapped_column(Double)
    pnl: Mapped[float | None] = mapped_column(Double)
    pnl_pct: Mapped[float | None] = mapped_column(Double)
    hold_days: Mapped[int | None] = mapped_column(Integer)
    close_reason: Mapped[str | None] = mapped_column(String(50))  # target_hit|stop_hit|manual|expired

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
