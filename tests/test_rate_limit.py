"""Tests for AlertRateLimiter and RateLimitedAlertDispatcher."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.rate_limit import AlertRateLimiter, RateLimitConfig
from pipewatch.alerting.rate_limited_dispatcher import RateLimitedAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(name: str = "my_job", success: bool = False) -> JobResult:
    return JobResult(job_name=name, success=success, error=None, metrics=MagicMock())


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.max_alerts == 5
        assert cfg.window_seconds == 3600

    def test_invalid_max_alerts_raises(self):
        with pytest.raises(ValueError, match="max_alerts"):
            RateLimitConfig(max_alerts=0)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(window_seconds=0)


# ---------------------------------------------------------------------------
# AlertRateLimiter
# ---------------------------------------------------------------------------

class TestAlertRateLimiter:
    def _make_limiter(self, max_alerts: int = 3, window_seconds: int = 60) -> AlertRateLimiter:
        return AlertRateLimiter(RateLimitConfig(max_alerts=max_alerts, window_seconds=window_seconds))

    def test_initially_allowed(self):
        limiter = self._make_limiter()
        assert limiter.is_allowed("job") is True

    def test_allowed_up_to_max(self):
        limiter = self._make_limiter(max_alerts=2)
        now = datetime.utcnow()
        limiter.record("job", now)
        assert limiter.is_allowed("job", now) is True
        limiter.record("job", now)
        assert limiter.is_allowed("job", now) is False

    def test_remaining_decreases_on_record(self):
        limiter = self._make_limiter(max_alerts=3)
        now = datetime.utcnow()
        assert limiter.remaining("job", now) == 3
        limiter.record("job", now)
        assert limiter.remaining("job", now) == 2

    def test_old_entries_pruned_outside_window(self):
        limiter = self._make_limiter(max_alerts=1, window_seconds=60)
        old = datetime.utcnow() - timedelta(seconds=120)
        limiter.record("job", old)
        now = datetime.utcnow()
        assert limiter.is_allowed("job", now) is True

    def test_independent_jobs(self):
        limiter = self._make_limiter(max_alerts=1)
        now = datetime.utcnow()
        limiter.record("job_a", now)
        assert limiter.is_allowed("job_a", now) is False
        assert limiter.is_allowed("job_b", now) is True


# ---------------------------------------------------------------------------
# RateLimitedAlertDispatcher
# ---------------------------------------------------------------------------

class TestRateLimitedAlertDispatcher:
    def _make_dispatcher(self, max_alerts: int = 2):
        inner = MagicMock()
        cfg = RateLimitConfig(max_alerts=max_alerts, window_seconds=60)
        dispatcher = RateLimitedAlertDispatcher(inner, config=cfg)
        return dispatcher, inner

    def test_forwards_within_limit(self):
        dispatcher, inner = self._make_dispatcher(max_alerts=3)
        result = _make_result()
        now = datetime.utcnow()
        dispatcher.dispatch(result, now)
        inner.dispatch.assert_called_once_with(result)

    def test_drops_alert_over_limit(self):
        dispatcher, inner = self._make_dispatcher(max_alerts=1)
        result = _make_result()
        now = datetime.utcnow()
        dispatcher.dispatch(result, now)
        dispatcher.dispatch(result, now)
        assert inner.dispatch.call_count == 1

    def test_exposes_limiter(self):
        dispatcher, _ = self._make_dispatcher()
        assert isinstance(dispatcher.limiter, AlertRateLimiter)
