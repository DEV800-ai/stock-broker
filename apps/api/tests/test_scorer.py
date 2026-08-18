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
