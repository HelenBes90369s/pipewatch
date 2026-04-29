"""Tests for pipewatch.alerting.suppressed_dispatcher."""

from datetime import time
from unittest.mock import MagicMock

from pipewatch.alerting.suppressed_dispatcher import SuppressedAlertDispatcher
from pipewatch.alerting.suppression import SuppressionSchedule, SuppressionWindow
from pipewatch.monitor import JobResult


def _make_result(success: bool = False) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.success = success
    r.job_name = "test_job"
    r.error = None if success else "boom"
    return r


def _make_inner(returns: bool = True):
    inner = MagicMock()
    inner.dispatch.return_value = returns
    return inner


def _always_suppressed() -> SuppressionSchedule:
    w = SuppressionWindow(start=time(0, 0), end=time(23, 59))
    return SuppressionSchedule([w])


def _never_suppressed() -> SuppressionSchedule:
    return SuppressionSchedule([])


class TestSuppressedAlertDispatcher:
    def test_dispatches_when_not_suppressed(self):
        inner = _make_inner(returns=True)
        dispatcher = SuppressedAlertDispatcher(
            notifiers=[], schedule=_never_suppressed(), inner=inner
        )
        result = dispatcher.dispatch(_make_result(success=False))
        assert result is True
        inner.dispatch.assert_called_once()

    def test_skips_dispatch_when_suppressed(self):
        inner = _make_inner(returns=True)
        dispatcher = SuppressedAlertDispatcher(
            notifiers=[], schedule=_always_suppressed(), inner=inner
        )
        result = dispatcher.dispatch(_make_result(success=False))
        assert result is False
        inner.dispatch.assert_not_called()

    def test_returns_false_when_inner_returns_false(self):
        inner = _make_inner(returns=False)
        dispatcher = SuppressedAlertDispatcher(
            notifiers=[], schedule=_never_suppressed(), inner=inner
        )
        result = dispatcher.dispatch(_make_result(success=False))
        assert result is False

    def test_schedule_property(self):
        schedule = _never_suppressed()
        dispatcher = SuppressedAlertDispatcher(
            notifiers=[], schedule=schedule, inner=_make_inner()
        )
        assert dispatcher.schedule is schedule

    def test_suppressed_on_success_still_silent(self):
        inner = _make_inner(returns=True)
        dispatcher = SuppressedAlertDispatcher(
            notifiers=[], schedule=_always_suppressed(), inner=inner
        )
        result = dispatcher.dispatch(_make_result(success=True))
        assert result is False
        inner.dispatch.assert_not_called()
