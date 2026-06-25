from datetime import datetime

from sqlalchemy import DateTime, Double, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("ticker", "source_url", name="uq_news_ticker_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sentiment: Mapped[str | None] = mapped_column(String(20))  # positive|negative|neutral
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    event_type: Mapped[str | None] = mapped_column(String(50), index=True)
    event_weight: Mapped[float | None] = mapped_column(Double)
    news_score: Mapped[float | None] = mapped_column(Double)
