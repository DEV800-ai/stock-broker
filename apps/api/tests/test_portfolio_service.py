from broker.models.paper_trade import PaperTrade
from broker.portfolio.service import _enrich_position


def make_trade(entry_price: float, shares: int, source: str = "paper") -> PaperTrade:
    return PaperTrade(ticker="AAPL", entry_price=entry_price, shares=shares, source=source)


def test_unrealized_pnl_with_current_price():
    trade = make_trade(entry_price=100.0, shares=10)
    pos = _enrich_position(trade, current_price=110.0)
    assert pos.unrealized_pnl == 100.0
    assert pos.unrealized_pnl_pct == 0.1


def test_unrealized_pnl_falls_back_to_entry_price_when_no_current_price():
    trade = make_trade(entry_price=50.0, shares=5)
    pos = _enrich_position(trade, current_price=None)
    assert pos.current_price == 50.0
    assert pos.unrealized_pnl == 0.0
    assert pos.unrealized_pnl_pct == 0.0


def test_negative_pnl():
    trade = make_trade(entry_price=200.0, shares=2)
    pos = _enrich_position(trade, current_price=180.0)
    assert pos.unrealized_pnl == -40.0
    assert pos.unrealized_pnl_pct == -0.1


def test_source_is_carried_through():
    trade = make_trade(entry_price=10.0, shares=1, source="manual_tradingview")
    pos = _enrich_position(trade, current_price=10.0)
    assert pos.source == "manual_tradingview"
