"""Tests for ThrottledAlertDispatcher."""

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.throttle import ThrottleConfig
from pipewatch.alerting.throttled_dispatcher import ThrottledAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(success: bool = False, job_name: str = "etl_job") -> JobResult:
    return JobResult(
        job_name=job_name,
        success=success,
        error_message=None if success else "Something failed",
        duration_seconds=12.5,
    )


def _make_notifier(returns: bool = True):
    notifier = MagicMock()
    notifier.send.return_value = returns
    return notifier


class TestThrottledAlertDispatcher:
    def _make_dispatcher(self, interval=0, max_per_hour=10):
        notifier = _make_notifier()
        cfg = ThrottleConfig(min_interval_seconds=interval, max_alerts_per_hour=max_per_hour)
        dispatcher = ThrottledAlertDispatcher(
            notifiers=[notifier],
            throttle_config=cfg,
        )
        return dispatcher, notifier

    def test_alert_sent_on_failure(self):
        dispatcher, notifier = self._make_dispatcher()
        result = _make_result(success=False)
        sent = dispatcher.dispatch(result)
        assert sent is True
        notifier.send.assert_called_once()

    def test_no_alert_on_success_by_default(self):
        dispatcher, notifier = self._make_dispatcher()
        result = _make_result(success=True)
        sent = dispatcher.dispatch(result)
        assert sent is False
        notifier.send.assert_not_called()

    def test_second_alert_blocked_by_throttle(self):
        dispatcher, notifier = self._make_dispatcher(interval=300)
        result = _make_result(success=False)
        dispatcher.dispatch(result)
        sent = dispatcher.dispatch(result)
        assert sent is False
        assert notifier.send.call_count == 1

    def test_throttle_records_after_send(self):
        dispatcher, notifier = self._make_dispatcher(interval=0)
        result = _make_result(success=False)
        dispatcher.dispatch(result)
        assert result.job_name in dispatcher.throttle._last_alert

    def test_throttle_not_recorded_when_no_alert_needed(self):
        dispatcher, notifier = self._make_dispatcher()
        result = _make_result(success=True)
        dispatcher.dispatch(result)
        assert result.job_name not in dispatcher.throttle._last_alert
