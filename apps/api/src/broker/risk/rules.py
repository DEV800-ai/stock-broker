"""Individual risk rules. Each takes a RiskContext and returns a RuleResult.

Rules are pure functions — no I/O, no DB, no LLM calls — so they can be
combined and unit-tested exhaustively. This module is the actual safety
boundary between AI proposals and broker execution; keep it boring.
"""
from broker.risk.types import RiskContext, RuleResult


def check_kill_switch(ctx: RiskContext) -> RuleResult:
    if ctx.is_killed:
        return RuleResult("kill_switch", False, ctx.kill_reason or "Agent kill switch is engaged", "block")
    return RuleResult("kill_switch", True, "Kill switch not engaged")


def check_autonomy_mode(ctx: RiskContext) -> RuleResult:
    if ctx.autonomy_mode == "research_only":
        return RuleResult("autonomy_mode", False, "Autonomy mode is research_only; no trades allowed", "block")
    if ctx.autonomy_mode == "paper_only":
        return RuleResult("autonomy_mode", False, "Autonomy mode is paper_only; live execution not allowed", "paper_only")
    return RuleResult("autonomy_mode", True, f"Autonomy mode {ctx.autonomy_mode} allows live proposals")


def check_no_margin(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.uses_margin:
        return RuleResult("no_margin", False, "Margin trading is not permitted in MVP", "block")
    return RuleResult("no_margin", True, "No margin used")


def check_no_options(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.is_option:
        return RuleResult("no_options", False, "Options trading is not permitted in MVP", "block")
    return RuleResult("no_options", True, "Not an options order")


def check_no_shorting(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.is_short:
        return RuleResult("no_shorting", False, "Short selling is not permitted in MVP", "block")
    return RuleResult("no_shorting", True, "Not a short sale")


def check_has_thesis(ctx: RiskContext) -> RuleResult:
    if not ctx.has_thesis:
        return RuleResult("has_thesis", False, "No thesis is attached to this trade proposal", "block")
    return RuleResult("has_thesis", True, "Thesis attached")


def check_liquidity(ctx: RiskContext) -> RuleResult:
    if ctx.avg_daily_volume is None:
        return RuleResult("liquidity", False, "Average daily volume unknown", "needs_manual_review")
    if ctx.avg_daily_volume < ctx.policy.min_avg_daily_volume:
        return RuleResult(
            "liquidity", False,
            f"Avg daily volume {ctx.avg_daily_volume:,.0f} is below minimum {ctx.policy.min_avg_daily_volume:,.0f}",
            "block",
        )
    return RuleResult("liquidity", True, "Liquidity sufficient")


def check_max_position_size(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.action != "BUY" or ctx.portfolio.net_liquidation <= 0:
        return RuleResult("max_position_size", True, "Not a buy, or no NLV to size against")
    existing = ctx.portfolio.position_values.get(ctx.proposal.ticker, 0.0)
    new_value = existing + ctx.proposal.estimated_value
    pct = new_value / ctx.portfolio.net_liquidation
    if pct > ctx.policy.max_position_pct:
        return RuleResult(
            "max_position_size", False,
            f"Resulting position would be {pct:.1%} of NLV, exceeding max {ctx.policy.max_position_pct:.1%}",
            "needs_smaller_size",
        )
    return RuleResult("max_position_size", True, f"Resulting position {pct:.1%} of NLV within limit")


def check_max_sector_exposure(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.action != "BUY" or not ctx.proposal.sector or ctx.portfolio.net_liquidation <= 0:
        return RuleResult("max_sector_exposure", True, "Not a buy, or sector unknown")
    existing = ctx.portfolio.sector_values.get(ctx.proposal.sector, 0.0)
    new_value = existing + ctx.proposal.estimated_value
    pct = new_value / ctx.portfolio.net_liquidation
    if pct > ctx.policy.max_sector_pct:
        return RuleResult(
            "max_sector_exposure", False,
            f"Resulting {ctx.proposal.sector} exposure would be {pct:.1%} of NLV, exceeding max {ctx.policy.max_sector_pct:.1%}",
            "needs_smaller_size",
        )
    return RuleResult("max_sector_exposure", True, f"Resulting sector exposure {pct:.1%} of NLV within limit")


def check_max_daily_loss(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.action != "BUY" or ctx.portfolio.net_liquidation <= 0:
        return RuleResult("max_daily_loss", True, "Not a buy, or no NLV to size against")
    loss_pct = -ctx.portfolio.realized_pnl_today / ctx.portfolio.net_liquidation
    if loss_pct >= ctx.policy.max_daily_loss_pct:
        return RuleResult(
            "max_daily_loss", False,
            f"Realized daily loss {loss_pct:.1%} has reached the {ctx.policy.max_daily_loss_pct:.1%} halt threshold",
            "block",
        )
    return RuleResult("max_daily_loss", True, f"Daily realized loss {loss_pct:.1%} within limit")


def check_max_weekly_loss(ctx: RiskContext) -> RuleResult:
    if ctx.proposal.action != "BUY" or ctx.portfolio.net_liquidation <= 0:
        return RuleResult("max_weekly_loss", True, "Not a buy, or no NLV to size against")
    loss_pct = -ctx.portfolio.realized_pnl_week / ctx.portfolio.net_liquidation
    if loss_pct >= ctx.policy.max_weekly_loss_pct:
        return RuleResult(
            "max_weekly_loss", False,
            f"Realized weekly loss {loss_pct:.1%} has reached the {ctx.policy.max_weekly_loss_pct:.1%} halt threshold",
            "block",
        )
    return RuleResult("max_weekly_loss", True, f"Weekly realized loss {loss_pct:.1%} within limit")


def check_earnings_proximity(ctx: RiskContext) -> RuleResult:
    if ctx.policy.allow_trade_before_earnings or not ctx.earnings_date or not ctx.today:
        return RuleResult("earnings_proximity", True, "No earnings blackout applies")
    days_to_earnings = (ctx.earnings_date - ctx.today).days
    if 0 <= days_to_earnings <= ctx.policy.earnings_blackout_days:
        return RuleResult(
            "earnings_proximity", False,
            f"Earnings in {days_to_earnings} day(s), within the {ctx.policy.earnings_blackout_days}-day blackout window",
            "needs_manual_review",
        )
    return RuleResult("earnings_proximity", True, "Not within earnings blackout window")


def check_cooldown(ctx: RiskContext) -> RuleResult:
    if ctx.recent_rejections >= ctx.policy.cooldown_rejections_threshold:
        return RuleResult(
            "cooldown", False,
            f"{ctx.recent_rejections} recent rejection(s) on {ctx.proposal.ticker} triggered a cooldown",
            "needs_manual_review",
        )
    if ctx.recent_losses >= ctx.policy.cooldown_losses_threshold:
        return RuleResult(
            "cooldown", False,
            f"{ctx.recent_losses} recent losing trade(s) on {ctx.proposal.ticker} triggered a cooldown",
            "needs_manual_review",
        )
    return RuleResult("cooldown", True, "No active cooldown")


RULES = [
    check_kill_switch,
    check_autonomy_mode,
    check_no_margin,
    check_no_options,
    check_no_shorting,
    check_has_thesis,
    check_liquidity,
    check_max_daily_loss,
    check_max_weekly_loss,
    check_max_position_size,
    check_max_sector_exposure,
    check_earnings_proximity,
    check_cooldown,
]
