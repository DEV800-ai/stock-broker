from datetime import date

from broker.ai.thesis_agent import _build_user_prompt
from broker.models.scan import ScanResult


def _scan(**overrides) -> ScanResult:
    fields = dict(
        ticker="AAPL", scan_date=date(2026, 11, 13), price=110.0,
        sma50=100.0, sma200=90.0, rsi_14=61.234,
        rs_excess_3m=0.052, rs_excess_6m=-0.013, volume_trend_ratio=1.21,
        macd=1.5, macd_signal=1.1, macd_histogram=0.4,
        bb_upper=115.0, bb_lower=95.0, bb_percent_b=0.75,
        pct_change_1d=0.031, gap_score=0.9,
        composite_score=0.62, momentum_score=0.7, rs_score=0.55, volume_score=0.6,
        signals_fired={"macd_bullish": True, "above_both_smas": True},
    )
    fields.update(overrides)
    return ScanResult(**fields)


def test_prompt_has_compact_technical_summary():
    p = _build_user_prompt("AAPL", _scan())
    assert "Trend: above SMA-50 (+10.0%); above SMA-200 (+22.2%); SMA-50 above SMA-200" in p
    assert "3-month +5.2%, 6-month -1.3%" in p
    assert "RSI-14 (Wilder): 61.2" in p
    assert "Volume trend (20-day avg vs 60-day avg): 1.21x" in p


def test_prompt_drops_raw_macd_bollinger_and_one_day_numbers():
    p = _build_user_prompt("AAPL", _scan())
    for gone in ("MACD (12,26,9)", "Bollinger", "%B", "1-day change", "gap="):
        assert gone not in p
    # signal flags themselves stay
    assert "macd_bullish" in p


def test_prompt_handles_missing_stats():
    p = _build_user_prompt("AAPL", _scan(sma200=None, rs_excess_6m=None, volume_trend_ratio=None))
    assert "SMA-200 N/A" in p
    assert "6-month N/A" in p
    assert "Volume trend (20-day avg vs 60-day avg): N/A" in p


def test_elliott_wave_removed_from_schema_and_prompts():
    from broker.ai import thesis_agent, thesis_translation
    from broker.models.thesis import StockThesis

    assert "elliott" not in thesis_agent._SYSTEM_PROMPT.lower()
    assert "elliott" not in thesis_translation._SYSTEM_PROMPT.lower()
    assert "elliott_wave_context" not in thesis_agent.ThesisResponse.model_fields
    assert "elliott_wave_context" not in StockThesis.__table__.columns
    # Old cached LLM output that still carries the key must still parse.
    parsed = thesis_agent.ThesisResponse.model_validate(
        {"why_interesting": "x", "risk_factors": "y", "elliott_wave_context": "wave 3"}
    )
    assert not hasattr(parsed, "elliott_wave_context")


def test_thesis_gate_is_raised_in_risk_off_regime(monkeypatch):
    import pytest

    import broker.ai.thesis_agent as ta

    agent = ta.ThesisAgent.__new__(ta.ThesisAgent)  # skip OpenAI client init
    agent.db = None
    monkeypatch.setattr(agent, "_load_scan", lambda *_: _scan(composite_score=0.60))
    monkeypatch.setattr(agent, "_find_cached", lambda *_: "cached-thesis")

    monkeypatch.setattr(ta, "latest_regime_label", lambda db: "risk_off")
    with pytest.raises(ValueError, match="risk_off"):
        agent.generate("AAPL")

    monkeypatch.setattr(ta, "latest_regime_label", lambda db: "risk_on")
    assert agent.generate("AAPL") == "cached-thesis"  # 0.60 clears the normal 0.50 bar

    # ad-hoc analysis is never gated
    monkeypatch.setattr(ta, "latest_regime_label", lambda db: "risk_off")
    assert agent.generate("AAPL", adhoc=True) == "cached-thesis"
