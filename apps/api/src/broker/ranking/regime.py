"""Market regime filter, derived from SPY's trend.

- risk_on:  SPY close > SMA-200 and SMA-50 is rising over the last 20 bars
- risk_off: SPY close < SMA-200
- neutral:  anything else (above SMA-200 but SMA-50 flat/falling)
- unknown:  not enough SPY history to tell (no effect anywhere)

Computed once per scan (scanner/runner.py) and stored on
ScanRun.params_json["regime"]. Effects:
- risk_off raises the effective thesis threshold to
  max(thesis_min_score, thesis_min_score_risk_off);
- risk_off applies RiskPolicyParams.risk_off_position_size_multiplier to the
  max position size (risk/rules.py::check_regime_position_size).

Descriptive market context — not a timing signal or recommendation.
"""
from __future__ import annotations

import pandas as pd

RISK_ON = "risk_on"
RISK_OFF = "risk_off"
NEUTRAL = "neutral"
UNKNOWN = "unknown"

_SMA_LONG = 200
_SMA_SHORT = 50
_SLOPE_BARS = 20


def compute_regime(spy_closes: pd.Series) -> dict:
    """Classify the regime from SPY daily closes (sorted ascending)."""
    closes = pd.Series(spy_closes, dtype="float64").dropna().reset_index(drop=True)
    out: dict = {
        "regime": UNKNOWN,
        "spy_close": float(closes.iloc[-1]) if len(closes) else None,
        "spy_sma200": None,
        "spy_sma50": None,
        "spy_sma50_slope_20d": None,
    }
    if len(closes) < _SMA_LONG:
        return out

    price = float(closes.iloc[-1])
    sma200 = float(closes.tail(_SMA_LONG).mean())
    sma50_series = closes.rolling(_SMA_SHORT).mean()
    sma50 = float(sma50_series.iloc[-1])
    sma50_prev = sma50_series.iloc[-1 - _SLOPE_BARS] if len(closes) > _SMA_SHORT + _SLOPE_BARS else None
    slope = (sma50 - float(sma50_prev)) / float(sma50_prev) if sma50_prev else None

    out.update(spy_sma200=sma200, spy_sma50=sma50, spy_sma50_slope_20d=slope)
    if price < sma200:
        out["regime"] = RISK_OFF
    elif price > sma200 and slope is not None and slope > 0:
        out["regime"] = RISK_ON
    else:
        out["regime"] = NEUTRAL
    return out


def effective_thesis_min_score(regime: str | None, settings=None) -> float:
    if settings is None:
        from broker.config import settings
    if regime == RISK_OFF:
        return max(settings.thesis_min_score, settings.thesis_min_score_risk_off)
    return settings.thesis_min_score


def latest_regime(db) -> dict | None:
    """Regime recorded on the most recent completed scan, with its run id/date."""
    from sqlalchemy import desc, select

    from broker.models.scan import ScanRun

    run = db.scalars(
        select(ScanRun)
        .where(ScanRun.status == "complete")
        .order_by(desc(ScanRun.started_at))
        .limit(1)
    ).first()
    if run is None or not (run.params_json or {}).get("regime"):
        return None
    return {
        **run.params_json["regime"],
        "scan_run_id": run.id,
        "as_of": run.finished_at or run.started_at,
    }


def latest_regime_label(db) -> str | None:
    info = latest_regime(db)
    return info.get("regime") if info else None
