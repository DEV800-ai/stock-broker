import pandas as pd

from broker.ranking.scorer import _bollinger_bands, _macd, compute_scores


def _closes(values: list[float]) -> pd.Series:
    return pd.Series(values)


def test_macd_returns_none_when_too_short():
    assert _macd(_closes([1.0] * 10)) == (None, None, None)


def test_macd_returns_values_with_enough_history():
    closes = _closes([100 + i * 0.5 for i in range(40)])
    macd_line, signal_line, histogram = _macd(closes)
    assert macd_line is not None
    assert signal_line is not None
    assert histogram is not None
    # steadily rising closes → positive MACD line
    assert macd_line > 0


def test_bollinger_bands_returns_none_when_too_short():
    assert _bollinger_bands(_closes([1.0] * 5)) == (None, None, None)


def test_bollinger_bands_flat_series_percent_b_is_none():
    upper, lower, percent_b = _bollinger_bands(_closes([100.0] * 20))
    assert upper == lower == 100.0
    assert percent_b is None


def test_bollinger_bands_price_above_upper_band():
    values = [100.0] * 19 + [200.0]
    upper, lower, percent_b = _bollinger_bands(_closes(values))
    assert percent_b > 1.0


def _make_bars(n: int, start: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=n)
    closes = [start + i * step for i in range(n)]
    return pd.DataFrame(
        {
            "bar_date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1_000_000] * n,
        }
    )


def test_compute_scores_includes_macd_and_bollinger_fields():
    bars = _make_bars(60)
    scores = compute_scores(bars)
    assert "macd" in scores
    assert "macd_signal" in scores
    assert "macd_histogram" in scores
    assert "bb_upper" in scores
    assert "bb_lower" in scores
    assert "bb_percent_b" in scores
    assert scores["macd"] is not None
    assert scores["bb_upper"] is not None


# --- v2 composite (1–3 month horizon) ----------------------------------------

from broker.ranking.scorer import (  # noqa: E402
    _composite,
    _momentum_score,
    _rs_score,
    _volume_score,
    _volume_trend_ratio,
    composite_weights,
    weights_version,
)


def test_default_weights_are_momentum_rs_volume():
    w = composite_weights()
    assert w == {"momentum": 0.40, "rs": 0.40, "volume": 0.20}
    assert weights_version(w) == "v2:m0.40-rs0.40-v0.20"


def test_composite_excludes_gap_score():
    bars = _make_bars(220)
    base = compute_scores(bars)
    # A huge gap-up on the last bar changes gap_score but not the composite.
    gapped = bars.copy()
    gapped.loc[gapped.index[-1], "open"] = gapped["close"].iloc[-2] * 1.2
    scores = compute_scores(gapped)
    assert scores["gap_score"] == 1.0
    assert base["gap_score"] != scores["gap_score"]
    assert scores["composite_score"] == base["composite_score"]


def test_composite_uses_configured_weights():
    bars = _make_bars(220)
    s = compute_scores(bars)
    expected = 0.4 * s["momentum_score"] + 0.4 * s["rs_score"] + 0.2 * s["volume_score"]
    assert abs(s["composite_score"] - expected) < 1e-12
    only_rs = compute_scores(bars, weights={"momentum": 0.0, "rs": 1.0, "volume": 0.0})
    assert only_rs["composite_score"] == s["rs_score"]


def test_composite_renormalises_over_available_scores():
    c = _composite({"momentum": 1.0, "rs": None, "volume": 0.0}, {"momentum": 0.4, "rs": 0.4, "volume": 0.2})
    assert abs(c - 0.4 / 0.6) < 1e-12
    assert _composite({"momentum": None, "rs": None, "volume": None}, composite_weights()) is None


def test_momentum_ignores_one_day_change():
    # Signature no longer takes pct_1d at all.
    assert _momentum_score(60.0, 0.05, True, True) == _momentum_score(60.0, 0.05, True, True)
    assert _momentum_score(None, None, True, False) == 0.5


def test_rs_score_mapping_matches_comment():
    assert _rs_score(-0.10, -0.10) == 0.0
    assert abs(_rs_score(0.05, 0.05) - 0.5) < 1e-12
    assert _rs_score(0.20, 0.20) == 1.0
    assert abs(_rs_score(0.0, 0.10) - 0.5) < 1e-12  # averaged
    assert abs(_rs_score(0.05, None) - 0.5) < 1e-12  # 6m missing → 3m only
    assert _rs_score(None, None) is None


def test_rs_uses_3m_and_6m_excess_vs_sector():
    bars = _make_bars(220, step=1.0)  # strong uptrend
    flat_sector = pd.DataFrame({"bar_date": bars["bar_date"], "close": [100.0] * 220})
    s = compute_scores(bars, flat_sector)
    own_3m = bars["close"].iloc[-1] / bars["close"].iloc[-64] - 1
    own_6m = bars["close"].iloc[-1] / bars["close"].iloc[-127] - 1
    assert abs(s["rs_excess_3m"] - own_3m) < 1e-12
    assert abs(s["rs_excess_6m"] - own_6m) < 1e-12
    same_as_sector = compute_scores(bars, bars[["bar_date", "close"]])
    assert same_as_sector["rs_excess_3m"] == 0.0
    assert abs(same_as_sector["rs_score"] - 1 / 3) < 1e-12
    assert s["pct_change_20d"] is not None  # 20-day stat still stored


def test_volume_trend_is_20d_vs_60d_average():
    vols = pd.Series([1_000_000.0] * 40 + [2_000_000.0] * 20)
    # 20d avg = 2M; 60d avg = (40*1M + 20*2M)/60 = 1.333M → 1.5x
    assert abs(_volume_trend_ratio(vols) - 1.5) < 1e-12
    assert _volume_trend_ratio(vols.tail(59)) is None
    assert _volume_score(0.75) == 0.0
    assert abs(_volume_score(1.125) - 0.5) < 1e-12
    assert _volume_score(1.5) == 1.0


def test_one_day_volume_spike_does_not_move_volume_score():
    bars = _make_bars(220)
    spiked = bars.copy()
    spiked.loc[spiked.index[-1], "volume"] = 3_000_000  # 3x surge: old formula scored this 1.0
    a, b = compute_scores(bars), compute_scores(spiked)
    assert b["volume_ratio"] == 3.0  # 1-day stat still stored
    assert b["signals_fired"]["volume_surge"]
    assert b["volume_score"] - a["volume_score"] < 0.1  # only 1/20 of the 20d avg


# --- RSI (Wilder) -------------------------------------------------------------

from broker.ranking.scorer import _rsi  # noqa: E402

# StockCharts "RSI" ChartSchool worked example (Wilder smoothing, 14 periods).
_SC_CLOSES = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89,
    46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.21, 46.25,
    45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57, 43.42, 42.66, 43.13,
]
_SC_RSI = [
    70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38,
    54.71, 50.42, 39.99, 41.46, 41.87, 45.46, 37.30, 33.08, 37.77,
]


def test_rsi_matches_wilder_reference_values():
    # Published table rounds intermediate averages to 2 dp (0.24 / 0.10), so it
    # differs from the unrounded computation by < 0.1 throughout.
    for i, expected in enumerate(_SC_RSI):
        got = _rsi(pd.Series(_SC_CLOSES[: 15 + i]))
        assert abs(got - expected) < 0.1, (i, got, expected)


def test_rsi_exact_wilder_recursion():
    # First 14 changes: avg gain = 3.34 / 14, avg loss = 1.40 / 14 (SMA seed).
    g0, l0 = 3.34 / 14, 1.40 / 14
    assert abs(_rsi(pd.Series(_SC_CLOSES[:15])) - (100 - 100 / (1 + g0 / l0))) < 1e-9
    # Next close 46.28 -> 46.00 is a 0.28 loss; Wilder: avg = (prev * 13 + x) / 14.
    g1, l1 = (g0 * 13 + 0.0) / 14, (l0 * 13 + 0.28) / 14
    assert abs(_rsi(pd.Series(_SC_CLOSES[:16])) - (100 - 100 / (1 + g1 / l1))) < 1e-9


def test_rsi_differs_from_simple_rolling_mean():
    closes = pd.Series(_SC_CLOSES)
    delta = closes.diff().dropna()
    sma_gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
    sma_loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
    sma_rsi = 100 - 100 / (1 + sma_gain / sma_loss)
    assert abs(_rsi(closes) - 37.77) < 0.1
    assert abs(sma_rsi - 37.77) > 1.0  # the old implementation was off


def test_rsi_edge_cases():
    assert _rsi(pd.Series([1.0] * 14)) is None  # too short
    assert _rsi(pd.Series([float(i) for i in range(30)])) == 100.0  # no losses
    assert _rsi(pd.Series([5.0] * 30)) is None  # no movement at all
    falling = _rsi(pd.Series([float(30 - i) for i in range(30)]))
    assert falling == 0.0


def test_macd_and_bollinger_do_not_feed_composite(monkeypatch):
    import broker.ranking.scorer as scorer

    bars = _make_bars(220)
    base = compute_scores(bars)
    monkeypatch.setattr(scorer, "_macd", lambda closes: (99.0, -99.0, 198.0))
    monkeypatch.setattr(scorer, "_bollinger_bands", lambda closes: (1.0, 0.0, 5.0))
    changed = compute_scores(bars)
    assert changed["composite_score"] == base["composite_score"]
    assert changed["signals_fired"]["macd_bullish"]  # flags still fire
    assert changed["signals_fired"]["above_upper_band"]
