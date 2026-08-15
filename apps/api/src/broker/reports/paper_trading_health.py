"""Paper-trading track-record reporting.

Not part of any order/risk decision path — read-only aggregation over
order_previews / risk_evaluations / paper_trades, meant to answer the
question docs/HARDENING_PLAN.md's Phase 4 gate asks: "has paper trading run
for a meaningful stretch with no risk-engine bugs found?" That's ultimately a
human judgment call, but this gives the evidence (verdict/fill/error
distributions, days of history) instead of requiring someone to query the DB
by hand.
"""
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from broker.models.order import OrderPreview
from broker.models.paper_trade import PaperTrade
from broker.models.risk import RiskEvaluationRecord


@dataclass
class SourceBreakdown:
    """Same trade-level stats as PaperTradingHealthReport, scoped to one PaperTrade.source."""

    trade_count: int = 0
    trade_status_counts: dict[str, int] = field(default_factory=dict)
    closed_trade_count: int = 0
    win_count: int = 0
    win_rate: float | None = None
    avg_pnl_pct: float | None = None
    # executed|executed_with_changes|rejected|watch_only|paper_tracked|cancelled.
    # Only populated for source="manual_tradingview".
    outcome_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class PaperTradingHealthReport:
    since: datetime | None
    generated_at: datetime

    earliest_activity: datetime | None
    days_of_history: float | None

    preview_count: int
    preview_status_counts: dict[str, int] = field(default_factory=dict)
    risk_verdict_counts: dict[str, int] = field(default_factory=dict)

    trade_count: int = 0
    trade_status_counts: dict[str, int] = field(default_factory=dict)
    fill_status_counts: dict[str, int] = field(default_factory=dict)
    trade_source_counts: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, SourceBreakdown] = field(default_factory=dict)

    closed_trade_count: int = 0
    win_count: int = 0
    win_rate: float | None = None
    avg_pnl_pct: float | None = None

    # avg (fill_price - theoretical_price) / theoretical_price, signed so
    # positive = fills were worse than the naive limit-price model expected.
    avg_entry_slippage_pct: float | None = None


def build_paper_trading_health_report(db: Session, since: date | None = None) -> PaperTradingHealthReport:
    since_dt = datetime.combine(since, datetime.min.time()) if since else None

    preview_stmt = select(OrderPreview)
    if since_dt:
        preview_stmt = preview_stmt.where(OrderPreview.created_at >= since_dt)
    previews = db.scalars(preview_stmt).all()

    preview_status_counts: dict[str, int] = {}
    for p in previews:
        preview_status_counts[p.status] = preview_status_counts.get(p.status, 0) + 1

    verdict_stmt = select(RiskEvaluationRecord)
    if since_dt:
        verdict_stmt = verdict_stmt.where(RiskEvaluationRecord.created_at >= since_dt)
    evaluations = db.scalars(verdict_stmt).all()

    risk_verdict_counts: dict[str, int] = {}
    for e in evaluations:
        risk_verdict_counts[e.verdict] = risk_verdict_counts.get(e.verdict, 0) + 1

    trade_stmt = select(PaperTrade)
    if since_dt:
        trade_stmt = trade_stmt.where(PaperTrade.created_at >= since_dt)
    trades = db.scalars(trade_stmt).all()

    trade_status_counts: dict[str, int] = {}
    fill_status_counts: dict[str, int] = {}
    trade_source_counts: dict[str, int] = {}
    trades_by_source: dict[str, list[PaperTrade]] = {}
    closed = []
    slippage_pcts: list[float] = []
    for t in trades:
        trade_status_counts[t.status] = trade_status_counts.get(t.status, 0) + 1
        if t.fill_status:
            fill_status_counts[t.fill_status] = fill_status_counts.get(t.fill_status, 0) + 1
        trade_source_counts[t.source] = trade_source_counts.get(t.source, 0) + 1
        trades_by_source.setdefault(t.source, []).append(t)
        if t.status == "closed":
            closed.append(t)
        if t.entry_price is not None and t.theoretical_entry_price:
            slippage_pcts.append((t.entry_price - t.theoretical_entry_price) / t.theoretical_entry_price)

    win_count = sum(1 for t in closed if (t.pnl or 0) > 0)
    win_rate = (win_count / len(closed)) if closed else None
    avg_pnl_pct = (sum(t.pnl_pct for t in closed if t.pnl_pct is not None) / len(closed)) if closed else None
    avg_slippage = (sum(slippage_pcts) / len(slippage_pcts)) if slippage_pcts else None

    by_source: dict[str, SourceBreakdown] = {}
    for source, source_trades in trades_by_source.items():
        source_status_counts: dict[str, int] = {}
        source_outcome_counts: dict[str, int] = {}
        source_closed = []
        for t in source_trades:
            source_status_counts[t.status] = source_status_counts.get(t.status, 0) + 1
            if t.outcome:
                source_outcome_counts[t.outcome] = source_outcome_counts.get(t.outcome, 0) + 1
            if t.status == "closed":
                source_closed.append(t)
        source_win_count = sum(1 for t in source_closed if (t.pnl or 0) > 0)
        by_source[source] = SourceBreakdown(
            trade_count=len(source_trades),
            trade_status_counts=source_status_counts,
            closed_trade_count=len(source_closed),
            win_count=source_win_count,
            win_rate=(source_win_count / len(source_closed)) if source_closed else None,
            avg_pnl_pct=(
                sum(t.pnl_pct for t in source_closed if t.pnl_pct is not None) / len(source_closed)
                if source_closed
                else None
            ),
            outcome_counts=source_outcome_counts,
        )

    earliest_candidates = [x.created_at for x in (*previews, *trades) if x.created_at]
    earliest_activity = min(earliest_candidates) if earliest_candidates else None
    days_of_history = (
        (datetime.utcnow() - earliest_activity).total_seconds() / 86400 if earliest_activity else None
    )

    return PaperTradingHealthReport(
        since=since_dt,
        generated_at=datetime.utcnow(),
        earliest_activity=earliest_activity,
        days_of_history=days_of_history,
        preview_count=len(previews),
        preview_status_counts=preview_status_counts,
        risk_verdict_counts=risk_verdict_counts,
        trade_count=len(trades),
        trade_status_counts=trade_status_counts,
        fill_status_counts=fill_status_counts,
        trade_source_counts=trade_source_counts,
        by_source=by_source,
        closed_trade_count=len(closed),
        win_count=win_count,
        win_rate=win_rate,
        avg_pnl_pct=avg_pnl_pct,
        avg_entry_slippage_pct=avg_slippage,
    )
