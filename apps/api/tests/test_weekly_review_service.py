from datetime import date, datetime

import broker.reports.weekly_review_service as weekly_review_service
from broker.models.performance_review import PerformanceReview
from broker.reports.paper_trading_health import PaperTradingHealthReport
from broker.reports.weekly_review_service import _json_safe, generate_weekly_review


class _FakeScalars:
    def __init__(self, result):
        self._result = result

    def first(self):
        return self._result


class _FakeSession:
    """Minimal stand-in: returns a preset row for the dedup lookup, records add/commit/refresh calls."""

    def __init__(self, existing: PerformanceReview | None):
        self._existing = existing
        self.added = []
        self.committed = False

    def scalars(self, _stmt):
        return _FakeScalars(self._existing)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        pass


def test_json_safe_converts_datetimes_to_strings():
    data = {"generated_at": datetime(2026, 8, 17, 12, 0, 0), "count": 3, "nested": {"since": None}}
    safe = _json_safe(data)
    assert safe["generated_at"] == "2026-08-17 12:00:00"
    assert safe["count"] == 3
    assert safe["nested"]["since"] is None


def test_period_window_defaults_to_trailing_seven_days():
    db = _FakeSession(existing=None)
    period_end = date(2026, 8, 17)

    stub_report = PaperTradingHealthReport(since=None, generated_at=datetime(2026, 8, 17), earliest_activity=None, days_of_history=None, preview_count=0)
    weekly_review_service.build_paper_trading_health_report = lambda db, since, until: stub_report

    review = generate_weekly_review(db, triggered_by="manual", period_end=period_end)

    assert review.period_start == date(2026, 8, 10)
    assert review.period_end == period_end
    assert review.triggered_by == "manual"
    assert db.committed is True
    assert len(db.added) == 1


def test_existing_review_for_same_period_is_returned_without_regenerating():
    existing = PerformanceReview(
        id=1, period_start=date(2026, 8, 10), period_end=date(2026, 8, 17), triggered_by="manual", report_json={}
    )
    db = _FakeSession(existing=existing)

    review = generate_weekly_review(db, triggered_by="manual", period_end=date(2026, 8, 17))

    assert review is existing
    assert db.committed is False
    assert db.added == []
