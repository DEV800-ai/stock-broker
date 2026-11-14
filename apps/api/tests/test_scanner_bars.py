"""Regression tests for scanner bar loading and yfinance date windows."""
from datetime import date, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from broker.data.yfinance_data import start_date_for_trading_days
from broker.models.price_bar import PriceBar
from broker.scanner.runner import _BARS_DAYS, load_recent_bars


@pytest.fixture()
def db():
    # PriceBar uses only portable column types, so an in-memory SQLite DB is
    # enough to exercise the ORDER BY / LIMIT behaviour.
    engine = create_engine("sqlite://")
    PriceBar.__table__.create(engine)
    with Session(engine) as session:
        yield session


def _seed(db: Session, ticker: str, n: int, first: date) -> list[date]:
    dates = [first + timedelta(days=i) for i in range(n)]
    db.add_all(
        PriceBar(ticker=ticker, bar_date=d, open=i, high=i, low=i, close=float(i), volume=1000)
        for i, d in enumerate(dates)
    )
    db.commit()
    return dates


def test_load_recent_bars_returns_newest_when_more_than_limit_stored(db):
    n = _BARS_DAYS + 80
    dates = _seed(db, "AAPL", n, date(2025, 1, 1))
    df = load_recent_bars(db, "AAPL", ["bar_date", "close"])

    assert len(df) == _BARS_DAYS
    assert df["bar_date"].iloc[-1] == dates[-1]  # newest bar is used
    assert df["bar_date"].iloc[0] == dates[n - _BARS_DAYS]
    assert df["bar_date"].is_monotonic_increasing  # re-sorted ascending
    assert df["close"].iloc[-1] == float(n - 1)


def test_load_recent_bars_is_bounded_and_ticker_scoped(db):
    _seed(db, "XLK", _BARS_DAYS + 5, date(2025, 1, 1))
    _seed(db, "MSFT", 10, date(2025, 1, 1))
    assert len(load_recent_bars(db, "XLK", ["bar_date", "close"])) == _BARS_DAYS
    assert len(load_recent_bars(db, "MSFT", ["bar_date", "close"])) == 10
    assert load_recent_bars(db, "NOPE", ["bar_date", "close"]).empty


@pytest.mark.parametrize("days", [20, 60, 220, 260])
@pytest.mark.parametrize("today", [date(2026, 1, 2), date(2026, 7, 6), date(2026, 11, 27)])
def test_start_date_covers_requested_trading_days(days, today):
    start = start_date_for_trading_days(days, today)
    weekdays = int(np.busday_count(start, today + timedelta(days=1)))
    # NYSE has ~10 full-day holidays a year; allow for that pro rata (+1).
    holidays = int(np.ceil(10 * (today - start).days / 365)) + 1
    assert weekdays - holidays >= days


def test_old_calendar_day_window_was_too_short_for_sma200():
    """Documents the bug: days + 10 calendar days can't hold 200 trading days."""
    today = date(2026, 11, 13)
    old_start = today - timedelta(days=220 + 10)
    assert np.busday_count(old_start, today) < 200


# --- pre-score universe filters -----------------------------------------------

import pandas as pd  # noqa: E402

from broker.scanner.runner import universe_filter_reason  # noqa: E402


def _bars(closes, volumes) -> pd.DataFrame:
    return pd.DataFrame({"close": closes, "volume": volumes})


def test_filter_passes_liquid_ticker_above_min_price():
    # $50 x 1M shares = $50M/day
    assert universe_filter_reason(_bars([50.0] * 30, [1_000_000] * 30), 5.0, 10e6) is None


def test_filter_rejects_low_price():
    assert universe_filter_reason(_bars([4.99] * 30, [50_000_000] * 30), 5.0, 10e6) == "min_price"


def test_filter_rejects_low_dollar_volume_not_share_volume():
    # 1.5M shares/day looks liquid, but at $6 that's only $9M/day.
    assert universe_filter_reason(_bars([6.0] * 30, [1_500_000] * 30), 5.0, 10e6) == "min_dollar_volume"


def test_filter_uses_last_20_bars_for_dollar_volume():
    closes = [50.0] * 40
    volumes = [10_000_000] * 20 + [100_000] * 20  # liquid long ago, thin recently
    assert universe_filter_reason(_bars(closes, volumes), 5.0, 10e6) == "min_dollar_volume"
    assert universe_filter_reason(_bars(closes, volumes[::-1]), 5.0, 10e6) is None


def test_filter_handles_missing_volume_and_empty():
    assert universe_filter_reason(_bars([50.0] * 20, [None] * 20), 5.0, 10e6) == "min_dollar_volume"
    assert universe_filter_reason(_bars([], []), 5.0, 10e6) == "no_bars"
