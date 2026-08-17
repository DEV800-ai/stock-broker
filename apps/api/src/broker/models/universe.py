from datetime import datetime

from sqlalchemy import Boolean, BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class StockUniverse(Base):
    __tablename__ = "stock_universe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(200))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    exchange: Mapped[str | None] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_refreshed: Mapped[datetime | None] = mapped_column(DateTime)
