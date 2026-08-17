from broker.ai.thesis_check_service import _has_meaningfully_changed
from broker.models.thesis import StockThesis


def make_thesis(confidence: str | None, news_score: float | None) -> StockThesis:
    return StockThesis(
        ticker="AAPL",
        why_interesting="x",
        risk_factors="y",
        confidence=confidence,
        news_score=news_score,
    )


def test_unchanged_confidence_and_score():
    old = make_thesis("medium", 0.5)
    new = make_thesis("medium", 0.55)
    assert _has_meaningfully_changed(old, new) is False


def test_confidence_change_is_flagged():
    old = make_thesis("medium", 0.5)
    new = make_thesis("high", 0.5)
    assert _has_meaningfully_changed(old, new) is True


def test_large_news_score_swing_is_flagged():
    old = make_thesis("medium", 0.2)
    new = make_thesis("medium", 0.5)
    assert _has_meaningfully_changed(old, new) is True


def test_small_news_score_swing_not_flagged():
    old = make_thesis("medium", 0.2)
    new = make_thesis("medium", 0.3)
    assert _has_meaningfully_changed(old, new) is False


def test_missing_news_score_does_not_crash():
    old = make_thesis("medium", None)
    new = make_thesis("medium", 0.5)
    assert _has_meaningfully_changed(old, new) is False
