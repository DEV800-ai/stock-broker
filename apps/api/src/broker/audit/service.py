"""Audit log writer.

Every state-changing action in the app (order approval/rejection, paper trade
approval/rejection/close, ...) should call log() as part of the same DB
transaction as the action itself, so the audit row and the action it
describes commit or roll back together — no action is ever unaudited because
a caller forgot to commit.

Rows are also hash-chained (prev_hash -> entry_hash) so that editing or
deleting a row after the fact — including directly in the database, bypassing
this module entirely — is detectable via verify_chain(), even though nothing
here can prevent someone with DB access from doing it. That's the honest
scope of "tamper-evident" for a single-Postgres-instance MVP: detection, not
prevention. A determined attacker with DB write access could recompute the
whole chain to hide their edit; a proper prevention story needs an
append-only store or an external anchor, which is out of scope here.
"""
import hashlib
import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.models.audit import AuditLog


def _entry_hash(prev_hash: str | None, actor: str, action: str, entity_type: str | None,
                 entity_id: int | None, details: dict | None) -> str:
    payload = json.dumps(
        {
            "prev_hash": prev_hash,
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log(
    db: Session,
    actor: str,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    # Lock the current tail of the chain so two concurrent writers can't both read the
    # same prev_hash and fork the chain. Fine for a single-operator app's write volume.
    last = db.scalars(
        select(AuditLog).order_by(desc(AuditLog.id)).limit(1).with_for_update()
    ).first()
    prev_hash = last.entry_hash if last else None

    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details,
        prev_hash=prev_hash,
        entry_hash=_entry_hash(prev_hash, actor, action, entity_type, entity_id, details),
    )
    db.add(entry)
    db.flush()
    return entry


class ChainVerification:
    def __init__(self, ok: bool, checked: int, broken_at_id: int | None, reason: str | None):
        self.ok = ok
        self.checked = checked
        self.broken_at_id = broken_at_id
        self.reason = reason


def verify_chain(db: Session) -> ChainVerification:
    """Walk every chained row in id order and recompute its hash, checking it matches
    what's stored and that prev_hash matches the previous chained row's entry_hash.
    Rows with entry_hash IS NULL (written before chaining existed) are skipped and
    reset the expected prev_hash — they're outside the chain by design, not a break."""
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    expected_prev: str | None = None
    checked = 0
    for row in rows:
        if row.entry_hash is None:
            expected_prev = None
            continue
        if row.prev_hash != expected_prev:
            return ChainVerification(
                ok=False, checked=checked, broken_at_id=row.id,
                reason=f"row {row.id}: prev_hash does not match the preceding chained row's entry_hash",
            )
        recomputed = _entry_hash(
            row.prev_hash, row.actor, row.action, row.entity_type, row.entity_id, row.details_json
        )
        if recomputed != row.entry_hash:
            return ChainVerification(
                ok=False, checked=checked, broken_at_id=row.id,
                reason=f"row {row.id}: stored entry_hash does not match its own recomputed hash — row contents were altered",
            )
        expected_prev = row.entry_hash
        checked += 1
    return ChainVerification(ok=True, checked=checked, broken_at_id=None, reason=None)
