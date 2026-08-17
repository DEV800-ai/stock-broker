"""Shared latest-price lookup, used by order preview sizing and portfolio valuation."""
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.models.price_bar import PriceBar
from broker.models.scan import ScanResult


def latest_price(db: Session, ticker: str) -> float | None:
    scan = db.scalars(
        select(ScanResult)
        .where(ScanResult.ticker == ticker)
        .order_by(desc(ScanResult.scan_date), desc(ScanResult.id))
    ).first()
    if scan and scan.price:
        return scan.price
    bar = db.scalars(
        select(PriceBar).where(PriceBar.ticker == ticker).order_by(desc(PriceBar.bar_date))
    ).first()
    return bar.close if bar else None
