from types import SimpleNamespace

import numpy as np
import pandas as pd

from broker.ranking.regime import compute_regime, effective_thesis_min_score


def _trend(n: int, start: float, end: float) -> list[float]:
    return list(np.linspace(start, end, n))


def test_risk_on_when_above_sma200_and_sma50_rising():
    r = compute_regime(pd.Series(_trend(250, 100, 150)))
    assert r["regime"] == "risk_on"
    assert r["spy_close"] > r["spy_sma200"]
    assert r["spy_sma50_slope_20d"] > 0


def test_risk_off_when_below_sma200():
    r = compute_regime(pd.Series(_trend(250, 150, 100)))
    assert r["regime"] == "risk_off"
    assert r["spy_close"] < r["spy_sma200"]


def test_neutral_when_above_sma200_but_sma50_falling():
    # Long rise, then a 60-bar pullback that keeps price above the 200-day
    # average while the 50-day average turns down.
    closes = _trend(190, 100, 200) + _trend(60, 200, 180)
    r = compute_regime(pd.Series(closes))
    assert r["spy_close"] > r["spy_sma200"]
    assert r["spy_sma50_slope_20d"] < 0
    assert r["regime"] == "neutral"


def test_unknown_without_enough_history():
    r = compute_regime(pd.Series(_trend(150, 100, 120)))
    assert r["regime"] == "unknown"
    assert r["spy_close"] == 120
    assert compute_regime(pd.Series([], dtype=float))["regime"] == "unknown"


def test_effective_thesis_threshold():
    s = SimpleNamespace(thesis_min_score=0.50, thesis_min_score_risk_off=0.65)
    assert effective_thesis_min_score("risk_off", s) == 0.65
    assert effective_thesis_min_score("risk_on", s) == 0.50
    assert effective_thesis_min_score("neutral", s) == 0.50
    assert effective_thesis_min_score(None, s) == 0.50
    # Never *lowers* the bar even if misconfigured.
    s.thesis_min_score_risk_off = 0.40
    assert effective_thesis_min_score("risk_off", s) == 0.50
