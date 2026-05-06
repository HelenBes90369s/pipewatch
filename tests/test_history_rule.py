"""Tests for pipewatch.alerting.history_rule."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewatch.alerting.history_rule import RecoveryAlertRule, StreakAlertRule
from pipewatch.history import JobHistory
from pipewatch.monitor import JobResult


def _make_result(job_name="etl", success=True, error=None):
    metrics = MagicMock()
    metrics.started_at = None
    metrics.elapsed_seconds.return_value = 5.0
    return JobResult(
        job_name=job_name,
        success=success,
        metrics=metrics,
        error_message=error,
    )


class TestStreakAlertRule:
    def test_no_alert_on_success(self, tmp_path):
        rule = StreakAlertRule(threshold=3, history=JobHistory(tmp_path / "h.jsonl"))
        assert rule.should_alert(_make_result(success=True)) is False

    def test_no_alert_below_threshold(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        rule = StreakAlertRule(threshold=3, history=h)
        h.record(_make_result(success=False))
        # Only 1 prior failure; adding a second still below threshold=3
        assert rule.should_alert(_make_result(success=False)) is False

    def test_alert_at_threshold(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        rule = StreakAlertRule(threshold=3, history=h)
        h.record(_make_result(success=False))
        h.record(_make_result(success=False))
        # should_alert records the third failure internally
        assert rule.should_alert(_make_result(success=False)) is True

    def test_alert_above_threshold(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        rule = StreakAlertRule(threshold=2, history=h)
        h.record(_make_result(success=False))
        h.record(_make_result(success=False))
        assert rule.should_alert(_make_result(success=False)) is True

    def test_streak_for_delegates_to_history(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        h.record(_make_result(success=False))
        rule = StreakAlertRule(history=h)
        assert rule.streak_for("etl") == 1

    def test_streak_resets_after_success(self, tmp_path):
        """A success followed by failures should not count prior failures toward the streak."""
        h = JobHistory(tmp_path / "h.jsonl")
        rule = StreakAlertRule(threshold=3, history=h)
        h.record(_make_result(success=False))
        h.record(_make_result(success=False))
        # A success resets the streak
        h.record(_make_result(success=True))
        # Only 1 failure after the reset; should not trigger threshold=3
        assert rule.should_alert(_make_result(success=False)) is False


class TestRecoveryAlertRule:
    def test_no_alert_on_failure(self, tmp_path):
        rule = RecoveryAlertRule(history=JobHistory(tmp_path / "h.jsonl"))
        assert rule.should_alert(_make_result(success=False)) is False

    def test_no_alert_on_success_with_no_prior_failures(self, tmp_path):
        rule = RecoveryAlertRule(history=JobHistory(tmp_path / "h.jsonl"))
        assert rule.should_alert(_make_result(success=True)) is False

    def test_alert_on_recovery_after_failures(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        h.record(_make_result(success=False))
        rule = RecoveryAlertRule(min_prior_failures=1, history=h)
        assert rule.should_alert(_make_result(success=True)) is True

    def test_no_alert_when_streak_below_min(self, tmp_path):
        h = JobHistory(tmp_path / "h.jsonl")
        h.record(_make_result(success=False))
