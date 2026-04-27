"""Tests for pipewatch.alerting.dispatcher."""
from unittest.mock import MagicMock
import pytest

from pipewatch.alerting.dispatcher import AlertDispatcher
from pipewatch.alerting.rules import AlertRule, AlertRuleSet
from pipewatch.monitor import JobResult


def _make_result(success: bool, elapsed: float = 5.0) -> JobResult:
    metrics = MagicMock()
    metrics.elapsed_seconds = elapsed
    return JobResult(job_name="test-job", success=success, metrics=metrics)


def _make_notifier(send_ok: bool = True) -> MagicMock:
    n = MagicMock()
    n.send.return_value = send_ok
    return n


class TestAlertDispatcher:
    def test_no_alert_on_success_by_default(self):
        notifier = _make_notifier()
        dispatcher = AlertDispatcher(notifiers=[notifier])
        result = dispatcher.dispatch(_make_result(success=True))
        notifier.send.assert_not_called()
        assert result["sent"] == 0
        assert result["skipped"] == 1

    def test_alert_on_failure_by_default(self):
        notifier = _make_notifier()
        dispatcher = AlertDispatcher(notifiers=[notifier])
        result = dispatcher.dispatch(_make_result(success=False))
        notifier.send.assert_called_once()
        assert result["sent"] == 1

    def test_alert_on_success_when_rule_set(self):
        notifier = _make_notifier()
        rs = AlertRuleSet(rules=[AlertRule(name="r", on_success=True, on_failure=False)])
        dispatcher = AlertDispatcher(notifiers=[notifier], rule_set=rs)
        result = dispatcher.dispatch(_make_result(success=True))
        notifier.send.assert_called_once()
        assert result["sent"] == 1

    def test_skipped_when_notifier_returns_false(self):
        notifier = _make_notifier(send_ok=False)
        dispatcher = AlertDispatcher(notifiers=[notifier])
        result = dispatcher.dispatch(_make_result(success=False))
        assert result["sent"] == 0
        assert result["skipped"] == 1

    def test_duration_exceeded_triggers_alert(self):
        notifier = _make_notifier()
        rs = AlertRuleSet(rules=[
            AlertRule(name="slow", on_failure=False, max_duration_seconds=10.0)
        ])
        dispatcher = AlertDispatcher(notifiers=[notifier], rule_set=rs)
        result = dispatcher.dispatch(_make_result(success=True, elapsed=60.0))
        notifier.send.assert_called_once()
        assert result["sent"] == 1

    def test_no_alert_when_no_notifiers(self):
        dispatcher = AlertDispatcher(notifiers=[])
        result = dispatcher.dispatch(_make_result(success=False))
        assert result["sent"] == 0
        assert result["triggered"] == []

    def test_triggered_contains_notifier_class_name(self):
        notifier = _make_notifier()
        type(notifier).__name__ = "SlackNotifier"
        dispatcher = AlertDispatcher(notifiers=[notifier])
        result = dispatcher.dispatch(_make_result(success=False))
        assert "SlackNotifier" in result["triggered"]
