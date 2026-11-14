"""Signal scoring for scanned tickers.

Each sub-score is 0.0–1.0. Composite is a weighted average of the
momentum/trend, relative-strength and volume-trend sub-scores, tuned for the
1–3 month holding horizon the thesis assumes. Weights come from settings
(``composite_weight_*``) so they can be re-tuned from the signal-outcome
report without a code change. ``gap_score`` is still computed and stored so
its predictive value can be measured, but it no longer feeds the composite.
"""
import math

import pandas as pd

# Bump when the *formulas* (not just the weights) change, so the
# signal-outcome report can compare results across scoring versions.
SCORING_FORMULA_VERSION = "v2"

RS_LOOKBACKS = (63, 126)  # ~3 and ~6 months of trading days


def composite_weights(settings=None) -> dict[str, float]:
    if settings is None:
        from broker.config import settings
    return {
        "momentum": settings.composite_weight_momentum,
        "rs": settings.composite_weight_rs,
        "volume": settings.composite_weight_volume,
    }


def weights_version(weights: dict[str, float]) -> str:
    """Stable label for a formula version + weight set, e.g. "v2:m0.40-rs0.40-v0.20"."""
    return (
        f"{SCORING_FORMULA_VERSION}:m{weights['momentum']:.2f}"
        f"-rs{weights['rs']:.2f}-v{weights['volume']:.2f}"
    )


def _wilder_smooth(values: pd.Series, period: int) -> pd.Series:
    """Wilder's moving average (TradingView ``ta.rma``): seeded with the simple
    mean of the first ``period`` values, then avg = (prev * (period-1) + x) / period,
    i.e. an EMA with alpha = 1/period (``ewm(alpha=1/period, adjust=False)``)."""
    out = pd.Series(float("nan"), index=values.index, dtype="float64")
    if len(values) < period:
        return out
    seeded = values.copy().astype("float64")
    seeded.iloc[: period - 1] = float("nan")
    seeded.iloc[period - 1] = float(values.iloc[:period].mean())
    smoothed = seeded.iloc[period - 1 :].ewm(alpha=1 / period, adjust=False).mean()
    out.iloc[period - 1 :] = smoothed.to_numpy()
    return out


def _rsi(closes: pd.Series, period: int = 14) -> float | None:
    """RSI with Wilder smoothing (matches TradingView / most charting platforms)."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    avg_gain = _wilder_smooth(delta.clip(lower=0), period)
    avg_loss = _wilder_smooth(-delta.clip(upper=0), period)
    gain, loss = float(avg_gain.iloc[-1]), float(avg_loss.iloc[-1])
    if math.isnan(gain) or math.isnan(loss):
        return None
    if loss == 0:
        return 100.0 if gain > 0 else None
    return 100 - (100 / (1 + gain / loss))


def _macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None, float | None]:
    if len(closes) < slow + signal:
        return None, None, None
    macd_line = closes.ewm(span=fast, adjust=False).mean() - closes.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def _bollinger_bands(
    closes: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[float | None, float | None, float | None]:
    """Returns (upper, lower, percent_b). percent_b is where price sits within the bands:
    0.0 = at the lower band, 1.0 = at the upper band, can fall outside [0, 1]."""
    if len(closes) < period:
        return None, None, None
    window = closes.tail(period)
    mean = float(window.mean())
    std = float(window.std())
    upper = mean + num_std * std
    lower = mean - num_std * std
    price = float(closes.iloc[-1])
    percent_b = (price - lower) / (upper - lower) if upper != lower else None
    return upper, lower, percent_b


def compute_scores(
    bars: pd.DataFrame,
    sector_bars: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
) -> dict:
    """Compute all signal scores from a DataFrame of daily OHLCV bars.

    bars: columns [bar_date, open, high, low, close, volume], sorted ascending.
    sector_bars: [bar_date, close] for the benchmark (sector ETF) used for
        relative strength.
    weights: composite weights {"momentum", "rs", "volume"}; defaults to settings.
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
    macd, macd_signal, macd_histogram = _macd(closes)
    bb_upper, bb_lower, bb_percent_b = _bollinger_bands(closes)

    # 1-day spike ratio: stored stat + volume_surge flag only (not scored).
    avg_vol_20 = float(volumes.tail(21).iloc[:-1].mean()) if len(volumes) >= 21 else None
    today_vol = float(today["volume"]) if today["volume"] else 0.0
    volume_ratio = (today_vol / avg_vol_20) if avg_vol_20 and avg_vol_20 > 0 else None
    # Accumulation: 20-day average volume vs 60-day average volume.
    volume_trend_ratio = _volume_trend_ratio(volumes)

    rs_excess_3m, rs_excess_6m = _rs_excess(closes, sector_bars)

    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else None
    gap_pct = ((float(today["open"]) - prev_close) / prev_close) if prev_close and today["open"] else None

    above_sma50 = (price > sma50) if sma50 else None
    above_sma200 = (price > sma200) if sma200 else None

    # --- sub-scores ---
    volume_score = _volume_score(volume_trend_ratio)
    momentum_score = _momentum_score(rsi_14, pct_change_5d, above_sma50, above_sma200)
    rs_score = _rs_score(rs_excess_3m, rs_excess_6m)
    gap_score = _gap_score(gap_pct)  # stored for measurement, not in composite

    weights = weights or composite_weights()
    composite = _composite(
        {"momentum": momentum_score, "rs": rs_score, "volume": volume_score}, weights
    )

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
    if macd is not None and macd_signal is not None and macd > macd_signal and (macd_histogram or 0) > 0:
        signals["macd_bullish"] = True
    if bb_percent_b is not None and bb_percent_b >= 1.0:
        signals["above_upper_band"] = True
    elif bb_percent_b is not None and bb_percent_b <= 0.0:
        signals["below_lower_band"] = True

    return {
        "price": price,
        "volume_ratio": volume_ratio,
        "volume_trend_ratio": volume_trend_ratio,
        "rs_excess_3m": rs_excess_3m,
        "rs_excess_6m": rs_excess_6m,
        "pct_change_1d": pct_change_1d,
        "pct_change_5d": pct_change_5d,
        "pct_change_20d": pct_change_20d,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "rsi_14": rsi_14,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_histogram": macd_histogram,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_percent_b": bb_percent_b,
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


def _composite(scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted average over the sub-scores that are available (re-normalised)."""
    valid = {k: v for k, v in scores.items() if v is not None and weights.get(k, 0) > 0}
    if not valid:
        return None
    total_weight = sum(weights[k] for k in valid)
    return sum(v * weights[k] for k, v in valid.items()) / total_weight


def _volume_trend_ratio(volumes: pd.Series) -> float | None:
    if len(volumes) < 60:
        return None
    avg_60 = float(volumes.tail(60).mean())
    if avg_60 <= 0:
        return None
    return float(volumes.tail(20).mean()) / avg_60


def _volume_score(volume_trend_ratio: float | None) -> float | None:
    if volume_trend_ratio is None:
        return None
    # 20d/60d avg volume: 0.75x → 0.0, 1.125x → 0.5, 1.5x → 1.0, clamped.
    return min(max((volume_trend_ratio - 0.75) / 0.75, 0.0), 1.0)


def _momentum_score(
    rsi: float | None,
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

    if pct_5d is not None:
        parts.append(min(max((pct_5d + 0.02) / 0.15, 0.0), 1.0))

    if above_sma50 is not None:
        parts.append(1.0 if above_sma50 else 0.0)

    if above_sma200 is not None:
        parts.append(1.0 if above_sma200 else 0.0)

    return float(sum(parts) / len(parts)) if parts else None


def _rs_excess(
    closes: pd.Series, sector_bars: pd.DataFrame | None
) -> tuple[float | None, float | None]:
    """Excess return vs the benchmark over ~3 and ~6 months (63/126 bars).

    Falls back to the ticker's absolute return when no benchmark bars exist.
    """
    bench = None
    if sector_bars is not None and not sector_bars.empty:
        bench = sector_bars.sort_values("bar_date").reset_index(drop=True)["close"]
    out: list[float | None] = []
    for n in RS_LOOKBACKS:
        own = _pct(closes, n)
        if own is None:
            out.append(None)
            continue
        if bench is None:
            out.append(own)
            continue
        b = _pct(bench, n)
        out.append(own - b if b is not None else None)
    return out[0], out[1]


def _rs_score(excess_3m: float | None, excess_6m: float | None) -> float | None:
    vals = [v for v in (excess_3m, excess_6m) if v is not None]
    if not vals:
        return None
    excess = sum(vals) / len(vals)
    # Mean 3m/6m excess vs benchmark: -10% → 0.0, +5% → 0.5, +20% → 1.0
    # i.e. (excess + 0.10) / 0.30, clamped to [0, 1].
    return min(max((excess + 0.10) / 0.30, 0.0), 1.0)


def _gap_score(gap_pct: float | None) -> float | None:
    if gap_pct is None:
        return None
    # negative gap → 0, +2% → ~0.2, +10% → 1.0
    return min(max(gap_pct / 0.10, 0.0), 1.0)
