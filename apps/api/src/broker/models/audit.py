from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from broker.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)  # user identifier or "system"
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    details_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Hash chain for tamper evidence — see audit/service.py. prev_hash is the previous
    # row's entry_hash (None for the very first row); entry_hash covers this row's own
    # fields plus prev_hash, so editing any row's stored data (this one or an earlier
    # one) breaks the chain from that point forward, detectable via verify_chain().
    # Nullable at the DB level so this migration doesn't need to fabricate hashes for
    # rows written before chaining existed (e.g. an already-deployed instance) — those
    # rows are simply outside the chain. Every row written by audit/service.py::log()
    # after this lands always has entry_hash populated.
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    entry_hash: Mapped[str | None] = mapped_column(String(64))
