from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class TrackedTicker(Base):
    """A ticker a signed-in user added to their personal watchlist ("My Trades").

    Scoped by `actor` (the session email, see broker.auth.require_actor) — not a
    users table, since this app has no user accounts beyond the OAuth session.
    """

    __tablename__ = "tracked_tickers"
    __table_args__ = (UniqueConstraint("actor", "ticker", name="uq_tracked_ticker_actor_ticker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
