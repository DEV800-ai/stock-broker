from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from broker.models.price_bar import PriceBar
from broker.models.universe import StockUniverse
from broker.routers.universe import count_tickers_with_bars


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    StockUniverse.__table__.create(engine)
    PriceBar.__table__.create(engine)
    with Session(engine) as session:
        yield session


def test_counts_universe_tickers_that_have_bars(db):
    db.add_all(StockUniverse(ticker=t, name=t, sector="Technology", exchange="NASDAQ") for t in ("AAA", "BBB", "CCC"))
    for t, n in (("AAA", 3), ("BBB", 1)):
        db.add_all(PriceBar(ticker=t, bar_date=date(2026, 1, d + 1), close=1.0) for d in range(n))
    # Bars for a ticker outside the universe are not counted.
    db.add(PriceBar(ticker="^VIX", bar_date=date(2026, 1, 1), close=15.0))
    db.commit()
    assert count_tickers_with_bars(db) == 2


def test_zero_when_no_bars(db):
    db.add(StockUniverse(ticker="AAA", name="A", sector="Technology", exchange="NASDAQ"))
    db.commit()
    assert count_tickers_with_bars(db) == 0
