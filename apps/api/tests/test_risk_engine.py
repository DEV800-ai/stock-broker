from datetime import date, timedelta

import pytest

from broker.risk.engine import evaluate
from broker.risk.types import PortfolioState, RiskContext, RiskPolicyParams, TradeProposal


def make_ctx(**overrides) -> RiskContext:
    proposal = overrides.pop(
        "proposal",
        TradeProposal(
            ticker="RKLB",
            action="BUY",
            order_type="LIMIT",
            shares=40,
            limit_price=12.40,
            estimated_value=496.0,
            sector="Aerospace",
            thesis_id=1,
        ),
    )
    portfolio = overrides.pop(
        "portfolio",
        PortfolioState(
            net_liquidation=25_000.0,
            cash=10_000.0,
            position_values={},
            sector_values={},
            realized_pnl_today=0.0,
            realized_pnl_week=0.0,
        ),
    )
    defaults = dict(
        proposal=proposal,
        portfolio=portfolio,
        policy=RiskPolicyParams(),
        has_thesis=True,
        autonomy_mode="preview_required",
        is_killed=False,
        avg_daily_volume=2_000_000,
        today=date(2026, 8, 3),
    )
    defaults.update(overrides)
    return RiskContext(**defaults)


def test_clean_proposal_is_approved():
    result = evaluate(make_ctx())
    assert result.verdict == "approved"
    assert all(r.passed for r in result.results)


def test_kill_switch_blocks_everything_else():
    ctx = make_ctx(
        is_killed=True,
        kill_reason="manual halt",
        proposal=TradeProposal(
            ticker="RKLB", action="BUY", order_type="LIMIT", shares=1,
            limit_price=12.4, estimated_value=12.4, uses_margin=True, is_option=True, is_short=True,
        ),
        has_thesis=False,
    )
    result = evaluate(ctx)
    assert result.verdict == "blocked"
    kill_result = next(r for r in result.results if r.rule == "kill_switch")
    assert not kill_result.passed
    assert kill_result.reason == "manual halt"


@pytest.mark.parametrize("field,value", [("uses_margin", True), ("is_option", True), ("is_short", True)])
def test_hard_blocked_trade_types(field, value):
    proposal = TradeProposal(
        ticker="RKLB", action="BUY", order_type="LIMIT", shares=10,
        limit_price=12.4, estimated_value=124.0, **{field: value},
    )
    result = evaluate(make_ctx(proposal=proposal))
    assert result.verdict == "blocked"


def test_no_thesis_blocks():
    result = evaluate(make_ctx(has_thesis=False))
    assert result.verdict == "blocked"
    assert not next(r for r in result.results if r.rule == "has_thesis").passed


def test_illiquid_ticker_blocks():
    result = evaluate(make_ctx(avg_daily_volume=10_000))
    assert result.verdict == "blocked"


def test_unknown_liquidity_needs_manual_review():
    result = evaluate(make_ctx(avg_daily_volume=None))
    assert result.verdict == "needs_manual_review"


def test_oversized_position_needs_smaller_size():
    proposal = TradeProposal(
        ticker="RKLB", action="BUY", order_type="LIMIT", shares=1000,
        limit_price=12.4, estimated_value=12_400.0, sector="Aerospace",
    )
    result = evaluate(make_ctx(proposal=proposal))
    assert result.verdict == "needs_smaller_size"
    assert not next(r for r in result.results if r.rule == "max_position_size").passed


def test_existing_position_counts_toward_max_position_size():
    proposal = TradeProposal(
        ticker="RKLB", action="BUY", order_type="LIMIT", shares=10,
        limit_price=12.4, estimated_value=124.0, sector="Aerospace",
    )
    portfolio = PortfolioState(
        net_liquidation=25_000.0, cash=10_000.0,
        position_values={"RKLB": 1_200.0}, sector_values={"Aerospace": 1_200.0},
    )
    result = evaluate(make_ctx(proposal=proposal, portfolio=portfolio,
                                policy=RiskPolicyParams(max_position_pct=0.05)))
    assert result.verdict == "needs_smaller_size"


def test_oversized_sector_exposure_needs_smaller_size():
    proposal = TradeProposal(
        ticker="RKLB", action="BUY", order_type="LIMIT", shares=10,
        limit_price=12.4, estimated_value=124.0, sector="Aerospace",
    )
    portfolio = PortfolioState(
        net_liquidation=25_000.0, cash=10_000.0,
        position_values={}, sector_values={"Aerospace": 6_200.0},
    )
    result = evaluate(make_ctx(proposal=proposal, portfolio=portfolio))
    assert result.verdict == "needs_smaller_size"
    assert not next(r for r in result.results if r.rule == "max_sector_exposure").passed


def test_daily_loss_halt_blocks_new_buys():
    portfolio = PortfolioState(net_liquidation=25_000.0, cash=10_000.0, realized_pnl_today=-1_000.0)
    result = evaluate(make_ctx(portfolio=portfolio, policy=RiskPolicyParams(max_daily_loss_pct=0.03)))
    assert result.verdict == "blocked"


def test_daily_loss_halt_does_not_block_sells():
    proposal = TradeProposal(
        ticker="RKLB", action="SELL", order_type="LIMIT", shares=10,
        limit_price=12.4, estimated_value=124.0, sector="Aerospace",
    )
    portfolio = PortfolioState(net_liquidation=25_000.0, cash=10_000.0, realized_pnl_today=-5_000.0)
    result = evaluate(make_ctx(proposal=proposal, portfolio=portfolio))
    assert result.verdict == "approved"


def test_weekly_loss_halt_blocks_new_buys():
    portfolio = PortfolioState(net_liquidation=25_000.0, cash=10_000.0, realized_pnl_week=-2_500.0)
    result = evaluate(make_ctx(portfolio=portfolio, policy=RiskPolicyParams(max_weekly_loss_pct=0.08)))
    assert result.verdict == "blocked"


def test_earnings_blackout_needs_manual_review():
    today = date(2026, 8, 3)
    result = evaluate(make_ctx(today=today, earnings_date=today + timedelta(days=1)))
    assert result.verdict == "needs_manual_review"


def test_earnings_outside_window_is_fine():
    today = date(2026, 8, 3)
    result = evaluate(make_ctx(today=today, earnings_date=today + timedelta(days=10)))
    assert result.verdict == "approved"


def test_allow_trade_before_earnings_overrides_blackout():
    today = date(2026, 8, 3)
    result = evaluate(make_ctx(
        today=today, earnings_date=today,
        policy=RiskPolicyParams(allow_trade_before_earnings=True),
    ))
    assert result.verdict == "approved"


def test_cooldown_after_repeated_rejections():
    result = evaluate(make_ctx(recent_rejections=2))
    assert result.verdict == "needs_manual_review"


def test_cooldown_after_repeated_losses():
    result = evaluate(make_ctx(recent_losses=2))
    assert result.verdict == "needs_manual_review"


def test_research_only_mode_blocks_all_proposals():
    result = evaluate(make_ctx(autonomy_mode="research_only"))
    assert result.verdict == "blocked"


def test_paper_only_mode_forces_paper_only_verdict():
    result = evaluate(make_ctx(autonomy_mode="paper_only"))
    assert result.verdict == "paper_only"


def test_paper_only_does_not_override_a_hard_block():
    result = evaluate(make_ctx(autonomy_mode="paper_only", is_killed=True, kill_reason="halt"))
    assert result.verdict == "blocked"


def test_block_takes_precedence_over_needs_smaller_size():
    proposal = TradeProposal(
        ticker="RKLB", action="BUY", order_type="LIMIT", shares=1000,
        limit_price=12.4, estimated_value=12_400.0, sector="Aerospace", is_option=True,
    )
    result = evaluate(make_ctx(proposal=proposal))
    assert result.verdict == "blocked"


def test_sell_action_skips_sizing_and_loss_checks():
    proposal = TradeProposal(
        ticker="RKLB", action="SELL", order_type="LIMIT", shares=1000,
        limit_price=12.4, estimated_value=12_400.0, sector="Aerospace",
    )
    portfolio = PortfolioState(net_liquidation=25_000.0, cash=10_000.0, realized_pnl_today=-2_000.0)
    result = evaluate(make_ctx(proposal=proposal, portfolio=portfolio))
    assert result.verdict == "approved"
