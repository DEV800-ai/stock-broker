"""Signal scoring for scanned tickers.

Each sub-score is 0.0–1.0. Composite is a weighted average.
"""
import math

import pandas as pd


def _rsi(closes: pd.Series, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if not math.isnan(val) else None


def compute_scores(bars: pd.DataFrame, sector_bars: pd.DataFrame | None = None) -> dict:
    """Compute all signal scores from a DataFrame of daily OHLCV bars.

    bars: columns [bar_date, open, high, low, close, volume], sorted ascending.
    sector_bars: same schema for the sector ETF (used for relative strength).
    Returns a dict matching ScanResult fields.
    """
    if bars.empty or len(bars) < 5:
        return {}

    bars = bars.sort_values("bar_date").reset_index(drop=True)
    closes = bars["close"]
    volumes = bars["volume"].astype(float)

    today = bars.iloc[-1]
    price = float(today["close"])

    # --- raw stats ---
    pct_change_1d = _pct(closes, 1)
    pct_change_5d = _pct(closes, 5)
    pct_change_20d = _pct(closes, 20)

    sma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else None
    sma50 = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    sma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None

    rsi_14 = _rsi(closes)

    avg_vol_20 = float(volumes.tail(21).iloc[:-1].mean()) if len(volumes) >= 21 else None
    today_vol = float(today["volume"]) if today["volume"] else 0.0
    volume_ratio = (today_vol / avg_vol_20) if avg_vol_20 and avg_vol_20 > 0 else None

    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else None
    gap_pct = ((float(today["open"]) - prev_close) / prev_close) if prev_close and today["open"] else None

    above_sma50 = (price > sma50) if sma50 else None
    above_sma200 = (price > sma200) if sma200 else None

    # --- sub-scores ---
    volume_score = _volume_score(volume_ratio)
    momentum_score = _momentum_score(rsi_14, pct_change_1d, pct_change_5d, above_sma50, above_sma200)
    rs_score = _rs_score(pct_change_20d, sector_bars)
    gap_score = _gap_score(gap_pct)

    # weighted composite
    weights = {"volume": 0.25, "momentum": 0.35, "rs": 0.30, "gap": 0.10}
    scores = {"volume": volume_score, "momentum": momentum_score, "rs": rs_score, "gap": gap_score}
    valid = {k: v for k, v in scores.items() if v is not None}
    if valid:
        total_weight = sum(weights[k] for k in valid)
        composite = sum(v * weights[k] for k, v in valid.items()) / total_weight
    else:
        composite = None

    signals: dict[str, bool] = {}
    if volume_ratio and volume_ratio >= 2.0:
        signals["volume_surge"] = True
    if rsi_14 and 50 <= rsi_14 <= 70:
        signals["rsi_momentum"] = True
    if pct_change_5d and pct_change_5d >= 0.05:
        signals["5d_breakout"] = True
    if gap_pct and gap_pct >= 0.02:
        signals["gap_up"] = True
    if above_sma50 and above_sma200:
        signals["above_both_smas"] = True

    return {
        "price": price,
        "volume_ratio": volume_ratio,
        "pct_change_1d": pct_change_1d,
        "pct_change_5d": pct_change_5d,
        "pct_change_20d": pct_change_20d,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "rsi_14": rsi_14,
        "above_sma50": above_sma50,
        "above_sma200": above_sma200,
        "volume_score": volume_score,
        "momentum_score": momentum_score,
        "rs_score": rs_score,
        "gap_score": gap_score,
        "composite_score": composite,
        "signals_fired": signals if signals else None,
    }


# --- helpers ---

def _pct(closes: pd.Series, n: int) -> float | None:
    if len(closes) < n + 1:
        return None
    past = float(closes.iloc[-(n + 1)])
    if past == 0:
        return None
    return float((closes.iloc[-1] - past) / past)


def _volume_score(volume_ratio: float | None) -> float | None:
    if volume_ratio is None:
        return None
    # 1x avg → 0.0, 3x avg → 1.0, capped
    return min(max((volume_ratio - 1.0) / 2.0, 0.0), 1.0)


def _momentum_score(
    rsi: float | None,
    pct_1d: float | None,
    pct_5d: float | None,
    above_sma50: bool | None,
    above_sma200: bool | None,
) -> float | None:
    parts: list[float] = []

    if rsi is not None:
        # 50–70 is sweet spot; outside that range scores lower
        if rsi < 30:
            parts.append(0.0)
        elif rsi < 50:
            parts.append((rsi - 30) / 20 * 0.3)
        elif rsi <= 70:
            parts.append(0.3 + (rsi - 50) / 20 * 0.7)
        else:
            # overbought — diminishing returns
            parts.append(max(1.0 - (rsi - 70) / 30 * 0.5, 0.5))

    if pct_1d is not None:
        parts.append(min(max((pct_1d + 0.02) / 0.08, 0.0), 1.0))

    if pct_5d is not None:
        parts.append(min(max((pct_5d + 0.02) / 0.15, 0.0), 1.0))

    if above_sma50 is not None:
        parts.append(1.0 if above_sma50 else 0.0)

    if above_sma200 is not None:
        parts.append(1.0 if above_sma200 else 0.0)

    return float(sum(parts) / len(parts)) if parts else None


def _rs_score(pct_20d: float | None, sector_bars: pd.DataFrame | None) -> float | None:
    if pct_20d is None:
        return None
    if sector_bars is None or sector_bars.empty:
        # no sector comparison — score based on absolute 20d return
        return min(max((pct_20d + 0.05) / 0.20, 0.0), 1.0)

    sector_bars = sector_bars.sort_values("bar_date").reset_index(drop=True)
    sector_pct = _pct(sector_bars["close"], 20)
    if sector_pct is None:
        return min(max((pct_20d + 0.05) / 0.20, 0.0), 1.0)

    excess = pct_20d - sector_pct
    # +5% excess → 0.5, +15% excess → 1.0, -10% excess → 0.0
    return min(max((excess + 0.10) / 0.25, 0.0), 1.0)


def _gap_score(gap_pct: float | None) -> float | None:
    if gap_pct is None:
        return None
    # negative gap → 0, +2% → ~0.2, +10% → 1.0
    return min(max(gap_pct / 0.10, 0.0), 1.0)
