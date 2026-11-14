import math

import pytest

from broker.orders.sizing import atr_stop_and_target, risk_sized_shares
from broker.risk.rules import check_has_stop
from broker.risk.types import PortfolioState, RiskContext, RiskPolicyParams, TradeProposal


def test_stop_is_two_atr_below_and_target_three_atr_above():
    stop, target = atr_stop_and_target(100.0, 2.5)
    assert stop == pytest.approx(95.0)
    assert target == pytest.approx(107.5)
    assert atr_stop_and_target(100.0, 2.5, stop_multiple=1.0, target_multiple=2.0) == (97.5, 105.0)


@pytest.mark.parametrize("atr", [None, 0.0, -1.0, math.nan])
def test_no_levels_without_usable_atr(atr):
    assert atr_stop_and_target(100.0, atr) is None


def test_no_levels_when_stop_would_be_non_positive():
    assert atr_stop_and_target(10.0, 6.0) is None


def test_risk_sized_shares_formula():
    # equity 100k * 1% = $1,000 at risk; entry 100, stop 95 → $5/share → 200 sh ($20k)
    assert risk_sized_shares(100.0, 95.0, 100_000, 0.01, max_position_value=50_000) == 200


def test_risk_sized_shares_capped_by_max_position():
    # Uncapped would be 200 sh = $20k, but max-position room is $5k → 50 sh.
    assert risk_sized_shares(100.0, 95.0, 100_000, 0.01, max_position_value=5_000) == 50
    assert risk_sized_shares(100.0, 95.0, 100_000, 0.01, max_position_value=-1_000) == 0


def test_risk_sized_shares_degenerate_inputs():
    assert risk_sized_shares(100.0, 100.0, 100_000, 0.01, 50_000) == 0
    assert risk_sized_shares(100.0, 101.0, 100_000, 0.01, 50_000) == 0
    assert risk_sized_shares(100.0, 95.0, 0.0, 0.01, 50_000) == 0


def _ctx(action="BUY", stop=None, limit=100.0) -> RiskContext:
    return RiskContext(
        proposal=TradeProposal(
            ticker="X", action=action, order_type="LIMIT", shares=1, limit_price=limit,
            estimated_value=limit, stop_price=stop,
        ),
        portfolio=PortfolioState(net_liquidation=100_000, cash=100_000),
        policy=RiskPolicyParams(),
        has_thesis=True,
    )


def test_has_stop_rule_blocks_buy_without_stop():
    r = check_has_stop(_ctx(stop=None))
    assert not r.passed and r.severity == "block"


def test_has_stop_rule_blocks_stop_at_or_above_entry():
    assert not check_has_stop(_ctx(stop=100.0)).passed
    assert not check_has_stop(_ctx(stop=101.0)).passed


def test_has_stop_rule_passes_valid_stop_and_sells():
    assert check_has_stop(_ctx(stop=95.0)).passed
    assert check_has_stop(_ctx(action="SELL", stop=None)).passed


def test_engine_blocks_buy_without_stop():
    from broker.risk.engine import evaluate

    ctx = _ctx(stop=None)
    ctx.avg_daily_volume = 5_000_000
    assert evaluate(ctx).verdict == "blocked"
    ctx.proposal.stop_price = 95.0
    assert evaluate(ctx).verdict == "approved"


def test_order_service_can_resolve_latest_price():
    # Regression: create_preview() called latest_price() without importing it,
    # so previews without an explicit limit_price raised NameError (HTTP 500).
    from broker.data.pricing import latest_price
    from broker.orders import service

    assert service.latest_price is latest_price
