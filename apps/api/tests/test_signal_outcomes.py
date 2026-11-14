from datetime import date, timedelta

import pandas as pd
import pytest

from broker.reports.signal_outcomes import (
    Observation,
    aggregate,
    assign_buckets,
    entry_index,
    excess_return,
    forward_return,
    group_stats,
    measure,
    spearman_ic,
)

D0 = date(2026, 1, 5)


def _series(values: list[float], start: date = D0, skip_weekends: bool = True) -> pd.Series:
    idx = pd.bdate_range(start, periods=len(values)) if skip_weekends else pd.date_range(start, periods=len(values))
    return pd.Series(values, index=[d.date() for d in idx], dtype=float)


# --- forward-return indexing -------------------------------------------------

def test_forward_return_counts_bars_not_calendar_days():
    closes = _series([100.0 + i for i in range(30)])  # business days only
    # entry = bar 0 (100), +5 bars = 105, even though 7 calendar days pass.
    assert forward_return(closes, D0, 5) == pytest.approx(0.05)


def test_entry_bar_is_last_bar_on_or_before_scan_date():
    closes = _series([100.0 + i for i in range(30)])
    saturday = D0 + timedelta(days=5)  # D0 is a Monday
    assert entry_index(closes, saturday) == 4  # Friday's bar
    assert forward_return(closes, saturday, 1) == pytest.approx(105 / 104 - 1)
    assert entry_index(closes, D0 - timedelta(days=1)) is None


def test_pending_horizon_is_none_never_zero():
    closes = _series([100.0] * 10)  # flat → a measured return would be 0.0
    assert forward_return(closes, D0, 5) == 0.0
    assert forward_return(closes, D0, 9) == 0.0
    assert forward_return(closes, D0, 10) is None  # not enough future bars
    assert forward_return(closes, D0, 60) is None


# --- excess-return math ------------------------------------------------------

def test_excess_return_math():
    assert excess_return(0.10, 0.04) == pytest.approx(0.06)
    assert excess_return(-0.02, 0.03) == pytest.approx(-0.05)
    assert excess_return(0.10, None) is None
    assert excess_return(None, 0.01) is None


def test_measure_fills_excess_vs_spy_and_sector_and_pending():
    closes = {
        "AAA": _series([100.0 + 2 * i for i in range(25)]),  # +10% at 5, +40% at 20
        "SPY": _series([100.0 + i for i in range(25)]),       # +5% at 5, +20% at 20
        "XLK": _series([100.0] * 25),                          # flat
    }
    o = measure(Observation("AAA", D0, {}, [], sector_etf="XLK"), closes)
    assert o.fwd[5] == pytest.approx(0.10)
    assert o.excess_spy[5] == pytest.approx(0.05)
    assert o.excess_sector[5] == pytest.approx(0.10)
    assert o.excess_spy[20] == pytest.approx(0.20)
    assert o.fwd[60] is None and o.excess_spy[60] is None  # pending


def test_benchmark_pending_makes_excess_pending():
    closes = {"AAA": _series([100.0] * 30), "SPY": _series([100.0] * 4)}
    o = measure(Observation("AAA", D0, {}, []), closes)
    assert o.fwd[5] == 0.0
    assert o.excess_spy[5] is None
    assert o.excess_sector[5] is None  # no sector ETF


# --- buckets -----------------------------------------------------------------

def test_assign_buckets_quintiles():
    values = [i / 10 for i in range(10)]
    buckets = assign_buckets(values)
    assert buckets == ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4", "Q5", "Q5"]


def test_assign_buckets_handles_none_ties_and_small_n():
    assert assign_buckets([0.5, None, 0.1]) == ["Q2", None, "Q1"]
    tied = assign_buckets([0.5] * 10)
    assert sorted(set(tied)) == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert assign_buckets([None, None]) == [None, None]


# --- stats / IC --------------------------------------------------------------

def test_group_stats():
    s = group_stats([0.10, -0.02, 0.04, None])
    assert s["n"] == 3
    assert s["mean"] == pytest.approx(0.04)
    assert s["median"] == pytest.approx(0.04)
    assert s["hit_rate"] == pytest.approx(2 / 3)
    assert group_stats([None]) == {"n": 0, "mean": None, "median": None, "hit_rate": None}


def test_spearman_ic_sign_on_perfectly_ranked_data():
    x = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert spearman_ic(x, [0.01, 0.02, 0.05, 0.10, 0.50])["ic"] == pytest.approx(1.0)
    assert spearman_ic(x, [0.5, 0.1, 0.05, 0.0, -0.3])["ic"] == pytest.approx(-1.0)


def test_spearman_ic_undefined_cases():
    assert spearman_ic([0.1, 0.2], [0.1, 0.2])["ic"] is None
    assert spearman_ic([0.3] * 5, [1, 2, 3, 4, 5])["ic"] is None
    assert spearman_ic([0.1, None, 0.3, 0.4], [1, 2, None, 4])["n"] == 2


# --- end-to-end aggregation on synthetic data ---------------------------------

def test_aggregate_perfectly_ranked_universe():
    n = 10
    spy = _series([100.0] * 80)
    closes = {"SPY": spy}
    obs = []
    for i in range(n):
        t = f"T{i}"
        # higher composite → steeper uptrend → higher forward excess return
        closes[t] = _series([100.0 * (1 + 0.002 * i) ** k for k in range(80)])
        score = i / n
        obs.append(
            measure(
                Observation(
                    t, D0,
                    {"composite_score": score, "rs_score": score, "volume_score": 1 - score,
                     "momentum_score": None, "gap_score": 0.5},
                    ["rsi_momentum"] if i % 2 else [],
                ),
                closes,
            )
        )
    # one observation scanned too recently for any horizon
    obs.append(measure(Observation("T9", D0 + timedelta(days=200), {"composite_score": 0.9}, []), closes))

    report = aggregate(obs, thesis_min_score=0.5)
    h20 = report["20"]
    assert h20["n_measured"] == n
    assert h20["n_pending"] == 1
    assert h20["ic"]["composite_score"]["ic"] == pytest.approx(1.0)
    assert h20["ic"]["rs_score"]["ic"] == pytest.approx(1.0)
    assert h20["ic"]["volume_score"]["ic"] == pytest.approx(-1.0)
    assert h20["ic"]["momentum_score"]["ic"] is None
    assert h20["ic"]["gap_score"]["ic"] is None  # constant score
    tiers = h20["by_tier"]
    assert tiers["above_threshold"]["vs_spy"]["n"] == 5
    assert tiers["above_threshold"]["vs_spy"]["mean"] > tiers["below_threshold"]["vs_spy"]["mean"]
    assert h20["by_bucket"]["Q5"]["vs_spy"]["mean"] > h20["by_bucket"]["Q1"]["vs_spy"]["mean"]
    assert h20["by_signal"]["rsi_momentum"]["vs_spy"]["n"] == 5
    assert h20["by_tier"]["below_threshold"]["vs_sector"]["n"] == 0  # no sector ETFs here
    assert report["60"]["n_measured"] == n
