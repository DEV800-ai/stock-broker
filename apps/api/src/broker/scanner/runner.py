import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError, StaleDataError

from broker.config import settings
from broker.data.universe_seed import SECTOR_ETF_MAP, SEED_TICKERS
from broker.data.yfinance_data import get_bars_bulk
from broker.models.price_bar import PriceBar
from broker.models.scan import ScanResult, ScanRun
from broker.models.universe import StockUniverse
from broker.models.watchlist import WatchlistEntry
from broker.ranking.scorer import compute_scores

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50
_BARS_DAYS = 220  # enough for SMA-200 + buffer


class ScanRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_full_scan(self) -> None:
        run = ScanRun(started_at=datetime.utcnow(), status="running")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        # Capture as a plain int now, while the row is known to exist. Any later
        # *read* of an expired ORM attribute (e.g. run.id after an intervening
        # commit) triggers a reload — if the row's been deleted meanwhile, that
        # reload raises ObjectDeletedError. Using run_id sidesteps that entirely.
        run_id = run.id

        try:
            self._seed_universe()
            tickers = self._active_tickers()
            logger.info("Scanning %d tickers", len(tickers))

            run.total_tickers = len(tickers)
            run.phase = "fetching_bars"
            run.tickers_processed = 0
            self.db.commit()

            self._fetch_and_store_bars(tickers, run_id)

            run = self.db.get(ScanRun, run_id)
            run.phase = "scoring"
            run.tickers_processed = 0
            self.db.commit()

            sector_bars_cache = self._load_sector_bars()
            results = self._score_all(tickers, sector_bars_cache, run_id)

            flagged = [r for r in results if r.composite_score is not None and r.composite_score >= settings.scanner_min_score]
            self._upsert_watchlist(flagged, today=date.today())

            run.status = "complete"
            run.finished_at = datetime.utcnow()
            run.tickers_scanned = len(tickers)
            run.tickers_flagged = len(flagged)
            self.db.commit()
            logger.info("Scan complete: %d scanned, %d flagged", len(tickers), len(flagged))
        except (ObjectDeletedError, StaleDataError):
            # The scan_runs row was deleted out from under us mid-scan (e.g. an
            # operator cleared a run they believed was stuck/orphaned). There's no
            # row left to write a "failed" status to — just roll back and stop.
            logger.warning("Scan run %s was deleted mid-scan; aborting cleanly", run_id)
            self.db.rollback()
        except Exception as exc:
            logger.exception("Scan failed")
            self.db.rollback()
            try:
                run = self.db.get(ScanRun, run_id)
            except (ObjectDeletedError, StaleDataError):
                run = None
                self.db.rollback()
            if run is None:
                logger.warning("Scan run %s was deleted mid-scan; could not record failure", run_id)
                return
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error_message = str(exc)
            self.db.commit()
            raise

    # ------------------------------------------------------------------

    def _seed_universe(self) -> None:
        existing = set(
            self.db.scalars(select(StockUniverse.ticker))
        )
        new_entries = [
            StockUniverse(ticker=t, name=n, sector=s, exchange=e)
            for t, n, s, e in SEED_TICKERS
            if t not in existing
        ]
        if new_entries:
            self.db.add_all(new_entries)
            self.db.commit()
            logger.info("Seeded %d new tickers into universe", len(new_entries))

    def _active_tickers(self) -> list[str]:
        rows = self.db.scalars(
            select(StockUniverse.ticker)
            .where(StockUniverse.active == True)
            .limit(settings.scanner_universe_size)
        )
        return list(rows)

    def _bump_progress(self, run_id: int, processed: int) -> None:
        run = self.db.get(ScanRun, run_id)
        if run is not None:
            run.tickers_processed = processed
            self.db.commit()

    def _fetch_and_store_bars(self, tickers: list[str], run_id: int) -> None:
        for i in range(0, len(tickers), _BATCH_SIZE):
            batch = tickers[i : i + _BATCH_SIZE]
            logger.debug("Fetching bars for batch %d–%d", i, i + len(batch))
            bars_map = get_bars_bulk(batch, days=_BARS_DAYS)
            for ticker, df in bars_map.items():
                if df.empty:
                    continue
                for _, row in df.iterrows():
                    stmt = (
                        insert(PriceBar)
                        .values(
                            ticker=ticker,
                            bar_date=row["bar_date"],
                            open=row.get("open"),
                            high=row.get("high"),
                            low=row.get("low"),
                            close=row["close"],
                            volume=int(row["volume"]) if row["volume"] else None,
                        )
                        .on_conflict_do_update(
                            constraint="uq_price_bars_ticker_date",
                            set_=dict(
                                open=row.get("open"),
                                high=row.get("high"),
                                low=row.get("low"),
                                close=row["close"],
                                volume=int(row["volume"]) if row["volume"] else None,
                                fetched_at=datetime.utcnow(),
                            ),
                        )
                    )
                    self.db.execute(stmt)
            self.db.commit()
            self._bump_progress(run_id, min(i + len(batch), len(tickers)))

    def _load_sector_bars(self) -> dict[str, object]:
        """Load price bar DataFrames for all sector ETFs from DB."""
        import pandas as pd

        etf_tickers = list(set(SECTOR_ETF_MAP.values()))
        result: dict[str, object] = {}
        for etf in etf_tickers:
            rows = self.db.execute(
                select(PriceBar.bar_date, PriceBar.close)
                .where(PriceBar.ticker == etf)
                .order_by(PriceBar.bar_date)
            ).fetchall()
            if rows:
                result[etf] = pd.DataFrame(rows, columns=["bar_date", "close"])
        return result

    def _score_all(self, tickers: list[str], sector_bars: dict, run_id: int) -> list[ScanResult]:
        import pandas as pd

        scan_date = date.today()
        # build ticker→sector map
        sector_map: dict[str, str] = dict(
            self.db.execute(select(StockUniverse.ticker, StockUniverse.sector)).fetchall()
        )

        results: list[ScanResult] = []
        for idx, ticker in enumerate(tickers, start=1):
            rows = self.db.execute(
                select(
                    PriceBar.bar_date,
                    PriceBar.open,
                    PriceBar.high,
                    PriceBar.low,
                    PriceBar.close,
                    PriceBar.volume,
                )
                .where(PriceBar.ticker == ticker)
                .order_by(PriceBar.bar_date)
                .limit(_BARS_DAYS)
            ).fetchall()

            if not rows:
                continue

            bars_df = pd.DataFrame(rows, columns=["bar_date", "open", "high", "low", "close", "volume"])
            sector = sector_map.get(ticker)
            etf = SECTOR_ETF_MAP.get(sector) if sector else None
            sector_df = sector_bars.get(etf) if etf else None

            scores = compute_scores(bars_df, sector_df)
            if not scores:
                continue

            result = ScanResult(
                run_id=run_id,
                ticker=ticker,
                scan_date=scan_date,
                **scores,
            )
            self.db.add(result)
            results.append(result)

            if idx % _BATCH_SIZE == 0:
                self.db.commit()
                self._bump_progress(run_id, idx)

        self.db.commit()
        self._bump_progress(run_id, len(tickers))
        # refresh to get IDs
        for r in results:
            self.db.refresh(r)
        return results

    def _upsert_watchlist(self, flagged: list[ScanResult], today: date) -> None:
        flagged_sorted = sorted(flagged, key=lambda r: r.composite_score or 0, reverse=True)
        for rank, result in enumerate(flagged_sorted, start=1):
            stmt = (
                insert(WatchlistEntry)
                .values(
                    ticker=result.ticker,
                    watchlist_date=today,
                    rank=rank,
                    status="watch",
                    composite_score=result.composite_score,
                    scan_result_id=result.id,
                )
                .on_conflict_do_update(
                    constraint="uq_watchlist_ticker_date",
                    set_=dict(
                        rank=rank,
                        composite_score=result.composite_score,
                        scan_result_id=result.id,
                    ),
                )
            )
            self.db.execute(stmt)
        self.db.commit()
        logger.info("Watchlist updated: %d entries for %s", len(flagged_sorted), today)
