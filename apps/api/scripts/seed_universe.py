#!/usr/bin/env python
"""Seed the stock_universe table from the static ticker list.

Usage:
    PYTHONPATH=src python scripts/seed_universe.py
    PYTHONPATH=src python scripts/seed_universe.py --enrich    # fetch yfinance metadata
    PYTHONPATH=src python scripts/seed_universe.py --conids    # resolve IBKR conids (needs Gateway)
"""
import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from broker.db import SessionLocal
from broker.models.universe import StockUniverse
from broker.data.universe_seed import SEED_TICKERS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def seed(enrich: bool = False, resolve_conids: bool = False) -> None:
    db = SessionLocal()
    try:
        existing = {row.ticker for row in db.scalars(select(StockUniverse))}
        new_count = 0
        updated_count = 0

        for ticker, name, sector, exchange in SEED_TICKERS:
            if ticker in existing:
                continue

            row = StockUniverse(
                ticker=ticker,
                name=name,
                sector=sector,
                exchange=exchange,
                active=True,
            )
            db.add(row)
            new_count += 1

        db.commit()
        logger.info("Inserted %d new tickers (%d already existed)", new_count, len(existing))

        if enrich:
            _enrich_yfinance(db, updated_count)

        if resolve_conids:
            _resolve_conids(db)

    finally:
        db.close()


def _enrich_yfinance(db, updated_count: int) -> None:
    from broker.data.yfinance_data import get_info

    rows = list(db.scalars(select(StockUniverse).where(StockUniverse.market_cap == None)))
    logger.info("Enriching %d tickers via yfinance...", len(rows))

    for i, row in enumerate(rows):
        info = get_info(row.ticker)
        if info.get("name"):
            row.name = info["name"]
        if info.get("sector") and row.sector is None:
            row.sector = info["sector"]
        if info.get("industry"):
            row.industry = info["industry"]
        if info.get("market_cap"):
            row.market_cap = info["market_cap"]
        if info.get("exchange") and row.exchange is None:
            row.exchange = info["exchange"]
        updated_count += 1

        if (i + 1) % 10 == 0:
            db.commit()
            logger.info("  enriched %d/%d", i + 1, len(rows))
            time.sleep(1)  # be polite to yfinance

    db.commit()
    logger.info("Enrichment complete. Updated %d rows.", updated_count)


def _resolve_conids(db) -> None:
    from broker.data.ibkr import IBKRClient

    client = IBKRClient()
    if not client.is_authenticated():
        logger.error("IBKR Gateway not authenticated. Start Gateway and log in first.")
        return

    rows = list(db.scalars(select(StockUniverse).where(StockUniverse.ibkr_conid == None)))
    logger.info("Resolving conids for %d tickers via IBKR...", len(rows))

    for i, row in enumerate(rows):
        conid = client.resolve_conid(row.ticker)
        if conid:
            row.ibkr_conid = conid
        else:
            logger.debug("No conid found for %s", row.ticker)

        if (i + 1) % 20 == 0:
            db.commit()
            logger.info("  resolved %d/%d", i + 1, len(rows))
            time.sleep(0.5)

    db.commit()
    logger.info("Conid resolution complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed stock universe")
    parser.add_argument("--enrich", action="store_true", help="Enrich metadata via yfinance")
    parser.add_argument("--conids", action="store_true", help="Resolve IBKR conids (needs Gateway)")
    args = parser.parse_args()
    seed(enrich=args.enrich, resolve_conids=args.conids)
