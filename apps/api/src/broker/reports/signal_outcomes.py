"""Signal-outcome measurement: does the composite score predict anything?

Read-only, computed on read (no table). For each ScanResult, measures the
forward return over N *trading bars* after the scan date (from price_bars),
the excess return vs SPY and vs the ticker's sector ETF, then aggregates by
score tier, composite-score quintile and each ``signals_fired`` key, plus a
Spearman information coefficient (IC) per sub-score.

Conventions
-----------
- Entry bar = the last stored bar on or before ``scan_date`` (the scanner
  scores today's bar, so this is the close the score was computed from).
- Forward return at horizon h = close of the h-th bar *after* the entry bar
  divided by the entry close, minus 1. Bars are counted, not calendar days.
- If fewer than h future bars exist (for the ticker or the benchmark), the
  horizon is **pending** and that observation is excluded from that horizon's
  stats. It is never reported as a zero return.
- Excess return = ticker return - benchmark return over the same bars.
- IC is the Spearman rank correlation, pooled across all measured
  observations, between a sub-score and the forward excess return vs SPY.

The core is pure functions over pandas Series so the math is unit-testable
with synthetic bars; ``build_signal_outcomes_report`` is the thin DB layer.

Descriptive research statistics only — not a recommendation to trade.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

HORIZONS: tuple[int, ...] = (5, 20, 60)
SCORE_FIELDS: tuple[str, ...] = (
    "volume_score",
    "momentum_score",
    "rs_score",
    "gap_score",
    "composite_score",
)
MARKET_BENCHMARK = "SPY"
N_BUCKETS = 5


# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


@dataclass
class Observation:
    """One ScanResult plus its measured forward returns."""

    ticker: str
    scan_date: date
    scores: dict[str, float | None]
    signals: list[str]
    sector_etf: str | None = None
    weights_version: str | None = None
    # horizon -> raw forward return / excess vs SPY / excess vs sector ETF.
    # Missing key (or None) == pending / not measurable.
    fwd: dict[int, float | None] = field(default_factory=dict)
    excess_spy: dict[int, float | None] = field(default_factory=dict)
    excess_sector: dict[int, float | None] = field(default_factory=dict)
    bucket: str | None = None


def entry_index(closes: pd.Series, scan_date: date) -> int | None:
    """Position of the last bar on or before ``scan_date``.

    ``closes`` is indexed by bar_date and sorted ascending.
    """
    if closes.empty:
        return None
    pos = int(closes.index.searchsorted(scan_date, side="right")) - 1
    return pos if pos >= 0 else None


def forward_return(closes: pd.Series, scan_date: date, horizon: int) -> float | None:
    """Return over the ``horizon`` bars following the scan-date bar, or None
    if that many future bars don't exist yet (pending)."""
    i = entry_index(closes, scan_date)
    if i is None or i + horizon >= len(closes):
        return None
    entry = float(closes.iloc[i])
    if entry == 0 or math.isnan(entry):
        return None
    exit_ = float(closes.iloc[i + horizon])
    if math.isnan(exit_):
        return None
    return exit_ / entry - 1.0


def excess_return(ret: float | None, bench: float | None) -> float | None:
    if ret is None or bench is None:
        return None
    return ret - bench


def measure(
    obs: Observation,
    closes: dict[str, pd.Series],
    horizons: tuple[int, ...] = HORIZONS,
) -> Observation:
    """Fill ``obs.fwd`` / ``excess_*`` from per-ticker close series."""
    own = closes.get(obs.ticker)
    spy = closes.get(MARKET_BENCHMARK)
    sector = closes.get(obs.sector_etf) if obs.sector_etf else None
    for h in horizons:
        r = forward_return(own, obs.scan_date, h) if own is not None else None
        obs.fwd[h] = r
        r_spy = forward_return(spy, obs.scan_date, h) if spy is not None else None
        obs.excess_spy[h] = excess_return(r, r_spy)
        r_sec = forward_return(sector, obs.scan_date, h) if sector is not None else None
        obs.excess_sector[h] = excess_return(r, r_sec)
    return obs


def assign_buckets(values: list[float | None], n_buckets: int = N_BUCKETS) -> list[str | None]:
    """Quantile bucket labels "Q1" (lowest) .. "Qn" (highest) for each value.

    Ties are broken by order so buckets stay (near) equal-sized. None values
    get no bucket. With fewer values than buckets, uses as many buckets as
    there are values.
    """
    s = pd.Series(values, dtype="float64")
    valid = s.dropna()
    out: list[str | None] = [None] * len(values)
    if valid.empty:
        return out
    q = min(n_buckets, len(valid))
    ranks = valid.rank(method="first")
    labels = pd.qcut(ranks, q=q, labels=[f"Q{i}" for i in range(1, q + 1)])
    for idx, label in labels.items():
        out[int(idx)] = str(label)
    return out


def group_stats(excess: list[float | None]) -> dict:
    """n, mean, median, hit rate (share with excess > 0) over measured values."""
    vals = [v for v in excess if v is not None and not math.isnan(v)]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "hit_rate": None}
    arr = np.asarray(vals, dtype=float)
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "hit_rate": float((arr > 0).mean()),
    }


def spearman_ic(x: list[float | None], y: list[float | None]) -> dict:
    """Spearman rank correlation between paired x and y (pairs with a None
    dropped). Implemented as Pearson correlation of average ranks, so no
    scipy dependency. Returns {"ic": None} when undefined (n < 3 or a
    constant series)."""
    df = pd.DataFrame({"x": x, "y": y}, dtype="float64").dropna()
    n = len(df)
    if n < 3:
        return {"ic": None, "n": n}
    rx = df["x"].rank(method="average").to_numpy()
    ry = df["y"].rank(method="average").to_numpy()
    if rx.std() == 0 or ry.std() == 0:
        return {"ic": None, "n": n}
    ic = float(np.corrcoef(rx, ry)[0, 1])
    return {"ic": ic, "n": n}


def _both_stats(group: list[Observation], h: int) -> dict:
    return {
        "vs_spy": group_stats([o.excess_spy.get(h) for o in group]),
        "vs_sector": group_stats([o.excess_sector.get(h) for o in group]),
    }


def aggregate(
    observations: list[Observation],
    thesis_min_score: float,
    horizons: tuple[int, ...] = HORIZONS,
) -> dict:
    """Aggregate measured observations into the report body (per horizon)."""
    buckets = assign_buckets([o.scores.get("composite_score") for o in observations])
    for o, b in zip(observations, buckets):
        o.bucket = b

    bucket_ranges: dict[str, dict] = {}
    for o in observations:
        if o.bucket is None:
            continue
        c = o.scores["composite_score"]
        r = bucket_ranges.setdefault(o.bucket, {"min_composite": c, "max_composite": c})
        r["min_composite"] = min(r["min_composite"], c)
        r["max_composite"] = max(r["max_composite"], c)

    out: dict[str, dict] = {}
    for h in horizons:
        measured = [o for o in observations if o.excess_spy.get(h) is not None]
        pending = [o for o in observations if o.fwd.get(h) is None]

        def _tier(o: Observation) -> str:
            c = o.scores.get("composite_score")
            return "above_threshold" if c is not None and c >= thesis_min_score else "below_threshold"

        tiers: dict[str, list[Observation]] = defaultdict(list)
        by_bucket: dict[str, list[Observation]] = defaultdict(list)
        by_signal: dict[str, list[Observation]] = defaultdict(list)
        by_version: dict[str, list[Observation]] = defaultdict(list)
        for o in measured:
            tiers[_tier(o)].append(o)
            if o.bucket:
                by_bucket[o.bucket].append(o)
            for sig in o.signals:
                by_signal[sig].append(o)
            by_version[o.weights_version or "unversioned"].append(o)

        out[str(h)] = {
            "horizon_bars": h,
            "n_measured": len(measured),
            "n_pending": len(pending),
            "all": _both_stats(measured, h),
            "by_tier": {k: _both_stats(v, h) for k, v in sorted(tiers.items())},
            "by_bucket": {
                k: {**bucket_ranges.get(k, {}), **_both_stats(v, h)}
                for k, v in sorted(by_bucket.items())
            },
            "by_signal": {k: _both_stats(v, h) for k, v in sorted(by_signal.items())},
            "by_weights_version": {k: _both_stats(v, h) for k, v in sorted(by_version.items())},
            "ic": {
                f: spearman_ic(
                    [o.scores.get(f) for o in measured],
                    [o.excess_spy.get(h) for o in measured],
                )
                for f in SCORE_FIELDS
            },
        }
    return out


# ---------------------------------------------------------------------------
# DB layer
# ---------------------------------------------------------------------------


def _load_closes(db, tickers: set[str], since: date | None) -> dict[str, pd.Series]:
    from sqlalchemy import select

    from broker.models.price_bar import PriceBar

    if not tickers:
        return {}
    stmt = select(PriceBar.ticker, PriceBar.bar_date, PriceBar.close).where(
        PriceBar.ticker.in_(sorted(tickers))
    )
    if since is not None:
        stmt = stmt.where(PriceBar.bar_date >= since)
    rows = db.execute(stmt).fetchall()
    if not rows:
        return {}
    df = pd.DataFrame(rows, columns=["ticker", "bar_date", "close"])
    return {
        t: g.sort_values("bar_date").set_index("bar_date")["close"].astype(float)
        for t, g in df.groupby("ticker")
    }


def build_signal_outcomes_report(
    db,
    since: date | None = None,
    horizons: tuple[int, ...] = HORIZONS,
    flagged_only: bool = False,
) -> dict:
    from sqlalchemy import select

    from broker.config import settings
    from broker.data.universe_seed import SECTOR_ETF_MAP
    from broker.models.scan import ScanResult, ScanRun
    from broker.models.universe import StockUniverse

    stmt = (
        select(ScanResult, ScanRun.params_json)
        .join(ScanRun, ScanRun.id == ScanResult.run_id)
        .where(ScanRun.status == "complete")
    )
    if since is not None:
        stmt = stmt.where(ScanResult.scan_date >= since)
    if flagged_only:
        stmt = stmt.where(ScanResult.composite_score >= settings.scanner_min_score)
    # Newest run last so it wins the per-(ticker, scan_date) dedup below.
    stmt = stmt.order_by(ScanResult.scan_date, ScanResult.run_id)

    latest: dict[tuple[str, date], tuple] = {}
    for result, params in db.execute(stmt).all():
        latest[(result.ticker, result.scan_date)] = (result, params or {})

    sector_map: dict[str, str] = dict(
        db.execute(select(StockUniverse.ticker, StockUniverse.sector)).fetchall()
    )

    observations: list[Observation] = []
    for result, params in latest.values():
        sector = sector_map.get(result.ticker)
        observations.append(
            Observation(
                ticker=result.ticker,
                scan_date=result.scan_date,
                scores={f: getattr(result, f) for f in SCORE_FIELDS},
                signals=sorted((result.signals_fired or {}).keys()),
                sector_etf=SECTOR_ETF_MAP.get(sector) if sector else None,
                weights_version=params.get("weights_version"),
            )
        )

    tickers = {o.ticker for o in observations} | {MARKET_BENCHMARK}
    tickers |= {o.sector_etf for o in observations if o.sector_etf}
    first_scan = min((o.scan_date for o in observations), default=None)
    # Entry bar can precede scan_date (weekend/holiday scan), so pad the window.
    bars_since = first_scan - timedelta(days=10) if first_scan else None
    closes = _load_closes(db, tickers, bars_since)
    for o in observations:
        measure(o, closes, horizons)

    return {
        "generated_at": datetime.utcnow(),
        "since": since,
        "flagged_only": flagged_only,
        "thesis_min_score": settings.thesis_min_score,
        "horizons": list(horizons),
        "n_observations": len(observations),
        "results": aggregate(observations, settings.thesis_min_score, horizons),
    }
