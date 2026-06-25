from datetime import date, datetime

from sqlalchemy import Date, DateTime, Double, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("ticker", "watchlist_date", name="uq_watchlist_ticker_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    watchlist_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # watch|research|paper|avoid
    composite_score: Mapped[float | None] = mapped_column(Double)
    scan_result_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_results.id"))
    thesis_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stock_theses.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
