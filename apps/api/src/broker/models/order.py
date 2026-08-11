from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class OrderPreview(Base):
    __tablename__ = "order_previews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    thesis_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stock_theses.id"))

    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY|SELL
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="LIMIT")
    limit_price: Mapped[float] = mapped_column(Double, nullable=False)
    time_in_force: Mapped[str] = mapped_column(String(10), default="DAY")

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    bull_case: Mapped[str | None] = mapped_column(Text)
    bear_case: Mapped[str | None] = mapped_column(Text)
    portfolio_impact: Mapped[str | None] = mapped_column(Text)

    risk_status: Mapped[str] = mapped_column(String(30), nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)

    # paper (default, all of Phase 3) | live_preview | live — see execution/base.py.
    # Always "paper" today; Phase 4 wiring will set this and branch on it in get_broker_adapter().
    execution_mode: Mapped[str] = mapped_column(String(20), default="paper")

    # pending (awaiting human decision) | approved | rejected | blocked (never entered the queue)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    paper_trade_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("paper_trades.id"))
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
