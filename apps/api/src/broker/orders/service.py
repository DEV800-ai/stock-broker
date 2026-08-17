"""Order preview creation and the human approval/rejection flow.

Bridges the DB (portfolio state, thesis, price history) to the pure
risk engine, then — on approval — executes through execution/paper_adapter.py
for paper trades, or hands off to manual_execution/service.py for
execution_mode="manual_tradingview" (human trades manually in TradingView,
then self-reports the outcome). There is no live broker execution path.
Every preview and its risk evaluation is persisted, approved or not, so
nothing proposed here is unaudited.
"""
from dataclasses import asdict
from datetime import date, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from broker.audit.service import log as audit_log
from broker.config import settings
from broker.data.finnhub import fetch_next_earnings_date
from broker.execution.base import BrokerAdapter, FillResult
from broker.execution.paper_adapter import PaperAdapter
from broker.models.order import OrderPreview
from broker.models.paper_trade import PaperTrade
from broker.models.price_bar import PriceBar
from broker.models.risk import AgentControl, RiskEvaluationRecord, RiskPolicy
from broker.models.thesis import StockThesis
from broker.models.universe import StockUniverse
from broker.risk.engine import evaluate as evaluate_risk
from broker.risk.types import PortfolioState, RiskContext, RiskPolicyParams, TradeProposal

EXECUTION_MODES = ("paper", "manual_tradingview")


class OrderPreviewNotFound(Exception):
    pass


class InvalidPreviewState(Exception):
    pass


class InvalidOrderRequest(Exception):
    pass


class PreviewExpired(Exception):
    pass


class PreviewBlockedAtApproval(Exception):
    def __init__(self, verdict: str) -> None:
        super().__init__(f"Risk re-evaluation at approval time returned verdict {verdict!r}; approval blocked")
        self.verdict = verdict


class FillRejected(Exception):
    def __init__(self, ticker: str, action: str) -> None:
        super().__init__(f"Simulated fill for {action} {ticker} was rejected: order size too large relative to liquidity")
        self.ticker = ticker
        self.action = action


# ------------------------------------------------------------------
# Context assembly
# ------------------------------------------------------------------

def _avg_daily_volume(db: Session, ticker: str, days: int = 20) -> float | None:
    bars = db.scalars(
        select(PriceBar).where(PriceBar.ticker == ticker).order_by(desc(PriceBar.bar_date)).limit(days)
    ).all()
    volumes = [b.volume for b in bars if b.volume]
    return (sum(volumes) / len(volumes)) if volumes else None


def _sector(db: Session, ticker: str) -> str | None:
    row = db.scalars(select(StockUniverse).where(StockUniverse.ticker == ticker)).first()
    return row.sector if row else None


def _exchange(db: Session, ticker: str) -> str | None:
    row = db.scalars(select(StockUniverse).where(StockUniverse.ticker == ticker)).first()
    return row.exchange if row else None


def tradingview_url(db: Session, ticker: str) -> str:
    """Deep-links to the chart only — TradingView has no documented way to prefill an
    order ticket (side/qty/price) from an external URL, so the caller must display the
    preview's order details separately for the user to copy/retype in TradingView."""
    exchange = _exchange(db, ticker) or "NASDAQ"
    return f"https://www.tradingview.com/chart/?symbol={exchange}:{ticker}"


def _sectors_for(db: Session, tickers: set[str]) -> dict[str, str]:
    if not tickers:
        return {}
    rows = db.scalars(select(StockUniverse).where(StockUniverse.ticker.in_(tickers))).all()
    return {r.ticker: r.sector for r in rows if r.sector}


def _load_policy_params(db: Session) -> RiskPolicyParams:
    params = asdict(RiskPolicyParams())
    rows = db.scalars(select(RiskPolicy).where(RiskPolicy.is_active.is_(True))).all()
    for row in rows:
        params.update(row.params_json or {})
    return RiskPolicyParams(**params)


def _agent_control(db: Session) -> AgentControl | None:
    return db.scalars(select(AgentControl).where(AgentControl.scope == "global")).first()


def get_broker_adapter() -> BrokerAdapter:
    """Always returns the paper adapter. There is no live execution path —
    execution_mode="manual_tradingview" previews skip this factory entirely and are
    settled via manual_execution/service.py once the human reports what happened."""
    return PaperAdapter()


def build_portfolio_state(db: Session) -> PortfolioState:
    open_trades = db.scalars(select(PaperTrade).where(PaperTrade.status == "open")).all()
    sectors = _sectors_for(db, {t.ticker for t in open_trades})

    position_values: dict[str, float] = {}
    sector_values: dict[str, float] = {}
    total_position_value = 0.0
    for trade in open_trades:
        value = (trade.entry_price or 0.0) * (trade.shares or 0)
        position_values[trade.ticker] = position_values.get(trade.ticker, 0.0) + value
        total_position_value += value
        sector = sectors.get(trade.ticker)
        if sector:
            sector_values[sector] = sector_values.get(sector, 0.0) + value

    today = date.today()
    week_start = today - timedelta(days=7)
    closed_today = db.scalars(
        select(PaperTrade).where(PaperTrade.status == "closed").where(PaperTrade.exit_date == today)
    ).all()
    closed_week = db.scalars(
        select(PaperTrade)
        .where(PaperTrade.status == "closed")
        .where(PaperTrade.exit_date >= week_start)
    ).all()

    net_liquidation = settings.paper_account_equity
    return PortfolioState(
        net_liquidation=net_liquidation,
        cash=net_liquidation - total_position_value,
        position_values=position_values,
        sector_values=sector_values,
        realized_pnl_today=sum(t.pnl or 0.0 for t in closed_today),
        realized_pnl_week=sum(t.pnl or 0.0 for t in closed_week),
    )


def _recent_rejections(db: Session, ticker: str) -> int:
    since = datetime.utcnow() - timedelta(days=settings.risk_cooldown_days)
    return db.scalar(
        select(func.count())
        .select_from(OrderPreview)
        .where(OrderPreview.ticker == ticker)
        .where(OrderPreview.status == "rejected")
        .where(OrderPreview.created_at >= since)
    ) or 0


def _recent_losses(db: Session, ticker: str) -> int:
    since = date.today() - timedelta(days=settings.risk_cooldown_days)
    return db.scalar(
        select(func.count())
        .select_from(PaperTrade)
        .where(PaperTrade.ticker == ticker)
        .where(PaperTrade.status == "closed")
        .where(PaperTrade.exit_date >= since)
        .where(PaperTrade.pnl < 0)
    ) or 0


def build_risk_context(
    db: Session, ticker: str, action: str, shares: int, limit_price: float, thesis_id: int | None
) -> RiskContext:
    has_thesis = bool(thesis_id and db.get(StockThesis, thesis_id))
    proposal = TradeProposal(
        ticker=ticker,
        action=action,
        order_type="LIMIT",
        shares=shares,
        limit_price=limit_price,
        estimated_value=shares * limit_price,
        sector=_sector(db, ticker),
        thesis_id=thesis_id,
    )
    control = _agent_control(db)
    return RiskContext(
        proposal=proposal,
        portfolio=build_portfolio_state(db),
        policy=_load_policy_params(db),
        has_thesis=has_thesis,
        autonomy_mode=control.autonomy_mode if control else "preview_required",
        is_killed=control.is_killed if control else False,
        kill_reason=control.killed_reason if control else None,
        earnings_date=fetch_next_earnings_date(ticker),
        today=date.today(),
        avg_daily_volume=_avg_daily_volume(db, ticker),
        recent_rejections=_recent_rejections(db, ticker),
        recent_losses=_recent_losses(db, ticker),
    )


def _describe_portfolio_impact(ctx: RiskContext) -> str:
    proposal, portfolio = ctx.proposal, ctx.portfolio
    if proposal.action != "BUY" or portfolio.net_liquidation <= 0:
        return f"Reduces existing {proposal.ticker} exposure."
    add_pct = proposal.estimated_value / portfolio.net_liquidation
    new_position_pct = (portfolio.position_values.get(proposal.ticker, 0.0) + proposal.estimated_value) / portfolio.net_liquidation
    if proposal.sector:
        new_sector_pct = (portfolio.sector_values.get(proposal.sector, 0.0) + proposal.estimated_value) / portfolio.net_liquidation
        sector_clause = f", and {proposal.sector} exposure to {new_sector_pct:.1%}"
    else:
        sector_clause = ""
    return (
        f"Adds {add_pct:.1%} of paper account equity to {proposal.ticker}, "
        f"bringing the position to {new_position_pct:.1%} of equity{sector_clause}."
    )


# ------------------------------------------------------------------
# Preview lifecycle
# ------------------------------------------------------------------

def create_preview(
    db: Session,
    ticker: str,
    action: str,
    reason: str,
    thesis_id: int | None = None,
    shares: int | None = None,
    amount_usd: float | None = None,
    limit_price: float | None = None,
    order_type: str = "LIMIT",
    time_in_force: str = "DAY",
    execution_mode: str = "paper",
) -> OrderPreview:
    ticker = ticker.upper()
    if action not in ("BUY", "SELL"):
        raise InvalidOrderRequest(f"action must be BUY or SELL, got {action!r}")
    if execution_mode not in EXECUTION_MODES:
        raise InvalidOrderRequest(f"execution_mode must be one of {EXECUTION_MODES}, got {execution_mode!r}")

    if limit_price is None:
        limit_price = latest_price(db, ticker)
        if limit_price is None:
            raise InvalidOrderRequest(f"No price available for {ticker}; provide limit_price explicitly")

    if shares is None:
        if amount_usd is None:
            raise InvalidOrderRequest("Provide either shares or amount_usd")
        shares = int(amount_usd // limit_price)
        if shares < 1:
            raise InvalidOrderRequest(
                f"amount_usd {amount_usd} does not buy at least 1 share at limit_price {limit_price}"
            )

    ctx = build_risk_context(db, ticker, action, shares, limit_price, thesis_id)
    evaluation = evaluate_risk(ctx)

    thesis = db.get(StockThesis, thesis_id) if thesis_id else None

    preview = OrderPreview(
        ticker=ticker,
        thesis_id=thesis_id,
        action=action,
        shares=shares,
        order_type=order_type,
        limit_price=limit_price,
        time_in_force=time_in_force,
        reason=reason,
        bull_case=thesis.why_interesting if thesis else None,
        bear_case=thesis.risk_factors if thesis else None,
        portfolio_impact=_describe_portfolio_impact(ctx),
        risk_status=evaluation.verdict,
        approval_required=True,
        execution_mode=execution_mode,
        status="blocked" if evaluation.verdict == "blocked" else "pending",
    )
    db.add(preview)
    db.flush()

    db.add(RiskEvaluationRecord(
        ticker=ticker,
        order_preview_id=preview.id,
        verdict=evaluation.verdict,
        rule_results_json=[asdict(r) for r in evaluation.results],
    ))
    audit_log(
        db, actor="system", action="propose_trade", entity_type="order_preview", entity_id=preview.id,
        details={"ticker": ticker, "action": action, "shares": shares, "verdict": evaluation.verdict},
    )
    db.commit()
    db.refresh(preview)
    return preview


def list_awaiting_manual_confirmation(db: Session) -> list[OrderPreview]:
    return list(
        db.scalars(
            select(OrderPreview)
            .where(OrderPreview.execution_mode == "manual_tradingview")
            .where(OrderPreview.status == "approved")
            .order_by(OrderPreview.approved_at)
        )
    )


def get_risk_results(db: Session, preview_id: int) -> list[dict] | None:
    record = db.scalars(
        select(RiskEvaluationRecord)
        .where(RiskEvaluationRecord.order_preview_id == preview_id)
        .order_by(desc(RiskEvaluationRecord.created_at))
    ).first()
    return record.rule_results_json if record else None


def approve_preview(db: Session, preview_id: int, approved_by: str = "human") -> OrderPreview:
    preview = db.get(OrderPreview, preview_id)
    if not preview:
        raise OrderPreviewNotFound(preview_id)
    if preview.status != "pending":
        raise InvalidPreviewState(f"Order preview {preview_id} is {preview.status}, not pending")

    age = datetime.utcnow() - preview.created_at
    if age > timedelta(minutes=settings.order_preview_ttl_minutes):
        raise PreviewExpired(
            f"Order preview {preview_id} is {age} old, exceeds "
            f"{settings.order_preview_ttl_minutes}-minute TTL; request a fresh preview"
        )

    # Portfolio state, cooldowns, and kill-switch status can all have changed since the
    # preview was created — re-run the risk engine now, not just at preview time, so a
    # still-fresh (within-TTL) preview can't slip past a rule that would now block it.
    reeval_ctx = build_risk_context(
        db, preview.ticker, preview.action, preview.shares, preview.limit_price, preview.thesis_id
    )
    reevaluation = evaluate_risk(reeval_ctx)
    db.add(RiskEvaluationRecord(
        ticker=preview.ticker,
        order_preview_id=preview.id,
        verdict=reevaluation.verdict,
        rule_results_json=[asdict(r) for r in reevaluation.results],
    ))
    if reevaluation.verdict == "blocked":
        preview.status = "blocked"
        preview.risk_status = reevaluation.verdict
        audit_log(
            db, actor=approved_by, action="approve_order_blocked_on_reeval",
            entity_type="order_preview", entity_id=preview.id,
            details={"ticker": preview.ticker, "verdict": reevaluation.verdict},
        )
        db.commit()
        raise PreviewBlockedAtApproval(reevaluation.verdict)

    if preview.execution_mode == "manual_tradingview":
        # No simulated fill: this preview is headed to a human manually trading in
        # TradingView, not the paper fill simulator. The resulting position (if any) is
        # recorded later via manual_execution.service.record_outcome, once the user
        # reports back what actually happened.
        preview.status = "approved"
        preview.approved_by = approved_by
        preview.approved_at = datetime.utcnow()
        audit_log(
            db, actor=approved_by, action="approve_order_manual_tradingview",
            entity_type="order_preview", entity_id=preview.id,
            details={"ticker": preview.ticker, "action": preview.action, "shares": preview.shares},
        )
        db.commit()
        db.refresh(preview)
        return preview

    avg_daily_volume = _avg_daily_volume(db, preview.ticker)
    open_trade: PaperTrade | None = None
    adapter = get_broker_adapter()

    if preview.action == "SELL":
        open_trade = db.scalars(
            select(PaperTrade)
            .where(PaperTrade.ticker == preview.ticker)
            .where(PaperTrade.status == "open")
            .order_by(desc(PaperTrade.entry_date), desc(PaperTrade.id))
        ).first()
        if not open_trade:
            raise InvalidPreviewState(f"No open paper trade for {preview.ticker} to sell")
        # Exits don't partial-fill in this model — PaperTrade can't represent a position
        # closed across two exit prices/dates without splitting the trade row. They can
        # still be rejected outright for an illiquid ticker.
        fill: FillResult = adapter.submit_order(
            preview.action, preview.ticker, preview.limit_price, open_trade.shares, avg_daily_volume,
            allow_partial=False,
        )
    else:
        fill = adapter.submit_order(
            preview.action, preview.ticker, preview.limit_price, preview.shares, avg_daily_volume,
            allow_partial=True,
        )

    if fill.status == "rejected":
        preview.status = "rejected"
        audit_log(
            db, actor=approved_by, action="approve_order_fill_rejected",
            entity_type="order_preview", entity_id=preview.id,
            details={
                "ticker": preview.ticker,
                "requested_shares": open_trade.shares if open_trade else preview.shares,
                "avg_daily_volume": avg_daily_volume,
            },
        )
        db.commit()
        raise FillRejected(preview.ticker, preview.action)

    if preview.action == "BUY":
        trade = PaperTrade(
            ticker=preview.ticker,
            thesis_id=preview.thesis_id,
            entry_price=fill.fill_price,
            theoretical_entry_price=fill.theoretical_price,
            requested_shares=preview.shares,
            shares=fill.filled_shares,
            fill_status=fill.status,
            status="open",
            entry_date=date.today(),
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
            notes=f"Opened from order_preview {preview.id}: {preview.reason}"
            + (f" (partial fill: {fill.filled_shares}/{preview.shares} shares)" if fill.status == "partial" else ""),
        )
        db.add(trade)
        db.flush()
        preview.paper_trade_id = trade.id
    else:
        open_trade.status = "closed"
        open_trade.exit_price = fill.fill_price
        open_trade.theoretical_exit_price = fill.theoretical_price
        open_trade.fill_status = fill.status
        open_trade.exit_date = date.today()
        open_trade.close_reason = "manual"
        if open_trade.entry_price and open_trade.shares:
            open_trade.pnl = (fill.fill_price - open_trade.entry_price) * open_trade.shares
            open_trade.pnl_pct = (fill.fill_price - open_trade.entry_price) / open_trade.entry_price
        if open_trade.entry_date:
            open_trade.hold_days = (date.today() - open_trade.entry_date).days
        preview.paper_trade_id = open_trade.id

    preview.status = "approved"
    preview.approved_by = approved_by
    preview.approved_at = datetime.utcnow()
    audit_log(
        db, actor=approved_by, action="approve_order", entity_type="order_preview", entity_id=preview.id,
        details={
            "ticker": preview.ticker,
            "fill_price": fill.fill_price,
            "fill_status": fill.status,
            "filled_shares": fill.filled_shares,
            "paper_trade_id": preview.paper_trade_id,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview


def reject_preview(db: Session, preview_id: int, rejected_by: str = "human") -> OrderPreview:
    preview = db.get(OrderPreview, preview_id)
    if not preview:
        raise OrderPreviewNotFound(preview_id)
    if preview.status != "pending":
        raise InvalidPreviewState(f"Order preview {preview_id} is {preview.status}, not pending")
    preview.status = "rejected"
    audit_log(
        db, actor=rejected_by, action="reject_order", entity_type="order_preview", entity_id=preview.id,
        details={"ticker": preview.ticker},
    )
    db.commit()
    db.refresh(preview)
    return preview
