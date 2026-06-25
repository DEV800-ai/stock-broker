#!/usr/bin/env python
"""Backfill 200 days of daily price bars for all active tickers in stock_universe.

Uses yfinance for historical data. Run after seed_universe.py.
For daily updates, just re-run — it upserts via INSERT ... ON CONFLICT DO UPDATE.

Usage:
    PYTHONPATH=src python scripts/backfill_prices.py
    PYTHONPATH=src python scripts/backfill_prices.py --days 60     # shorter backfill
    PYTHONPATH=src python scripts/backfill_prices.py --batch 50    # tickers per batch
"""
import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def backfill(days: int = 200, batch_size: int = 50) -> None:
    from sqlalchemy import select, text
    from broker.db import SessionLocal, engine
    from broker.models.universe import StockUniverse
    from broker.data.yfinance_data import get_bars_bulk

    db = SessionLocal()
    try:
        tickers = list(db.scalars(select(StockUniverse.ticker).where(StockUniverse.active == True)))
        logger.info("Backfilling %d tickers, %d days each...", len(tickers), days)

        total_bars = 0
        for batch_start in range(0, len(tickers), batch_size):
            batch = tickers[batch_start: batch_start + batch_size]
            logger.info("Batch %d/%d: %s ... %s",
                        batch_start // batch_size + 1,
                        (len(tickers) + batch_size - 1) // batch_size,
                        batch[0], batch[-1])

            bars_map = get_bars_bulk(batch, days=days)

            rows_to_upsert = []
            for ticker, df in bars_map.items():
                for _, row in df.iterrows():
                    rows_to_upsert.append({
                        "ticker": row["ticker"],
                        "bar_date": row["bar_date"],
                        "open": float(row["open"]) if row["open"] == row["open"] else None,
                        "high": float(row["high"]) if row["high"] == row["high"] else None,
                        "low": float(row["low"]) if row["low"] == row["low"] else None,
                        "close": float(row["close"]),
                        "volume": int(row["volume"]),
                    })

            if rows_to_upsert:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO price_bars (ticker, bar_date, open, high, low, close, volume)
                            VALUES (:ticker, :bar_date, :open, :high, :low, :close, :volume)
                            ON CONFLICT (ticker, bar_date) DO UPDATE
                            SET open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low  = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume,
                                fetched_at = now()
                        """),
                        rows_to_upsert,
                    )
                total_bars += len(rows_to_upsert)
                logger.info("  upserted %d bars", len(rows_to_upsert))

            time.sleep(1)  # be polite to yfinance between batches

        logger.info("Backfill complete. Total bars upserted: %d", total_bars)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill price bars")
    parser.add_argument("--days", type=int, default=200, help="Days of history to fetch (default 200)")
    parser.add_argument("--batch", type=int, default=50, help="Tickers per yfinance batch (default 50)")
    args = parser.parse_args()
    backfill(days=args.days, batch_size=args.batch)
