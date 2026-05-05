"""Tests for pipewatch.alerting.deduplication."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from pipewatch.alerting.deduplication import AlertDeduplicator, DeduplicationConfig
from pipewatch.monitor import JobResult


def _make_result(name: str = "my_job", success: bool = False, error: str = "") -> JobResult:
    return JobResult(job_name=name, success=success, error_message=error, duration_seconds=1.0)


class TestDeduplicationConfig:
    def test_defaults(self):
        cfg = DeduplicationConfig()
        assert cfg.window_seconds == 300
        assert cfg.include_error_message is False

    def test_custom_values(self):
        cfg = DeduplicationConfig(window_seconds=60, include_error_message=True)
        assert cfg.window_seconds == 60
        assert cfg.include_error_message is True


class TestAlertDeduplicator:
    def _make_dedup(self, **kwargs) -> AlertDeduplicator:
        return AlertDeduplicator(DeduplicationConfig(**kwargs))

    def test_not_duplicate_before_record(self):
        dedup = self._make_dedup()
        result = _make_result()
        assert dedup.is_duplicate(result) is False

    def test_is_duplicate_after_record(self):
        dedup = self._make_dedup()
        result = _make_result()
        dedup.record(result)
        assert dedup.is_duplicate(result) is True

    def test_different_job_not_duplicate(self):
        dedup = self._make_dedup()
        dedup.record(_make_result(name="job_a"))
        assert dedup.is_duplicate(_make_result(name="job_b")) is False

    def test_different_status_not_duplicate(self):
        dedup = self._make_dedup()
        dedup.record(_make_result(success=False))
        assert dedup.is_duplicate(_make_result(success=True)) is False

    def test_error_message_ignored_by_default(self):
        dedup = self._make_dedup(include_error_message=False)
        dedup.record(_make_result(error="timeout"))
        assert dedup.is_duplicate(_make_result(error="connection refused")) is True

    def test_error_message_included_when_configured(self):
        dedup = self._make_dedup(include_error_message=True)
        dedup.record(_make_result(error="timeout"))
        assert dedup.is_duplicate(_make_result(error="connection refused")) is False

    def test_pending_count_increments(self):
        dedup = self._make_dedup()
        result = _make_result()
        dedup.record(result)
        dedup.record(result)
        assert dedup.pending_count(result) == 2

    def test_pending_count_zero_when_not_recorded(self):
        dedup = self._make_dedup()
        assert dedup.pending_count(_make_result()) == 0

    def test_expires_after_window(self):
        dedup = self._make_dedup(window_seconds=10)
        result = _make_result()
        start = 1000.0
        with patch("pipewatch.alerting.deduplication.time.monotonic", return_value=start):
            dedup.record(result)
        # Advance past the window
        with patch("pipewatch.alerting.deduplication.time.monotonic", return_value=start + 11):
            assert dedup.is_duplicate(result) is False

    def test_still_duplicate_within_window(self):
        dedup = self._make_dedup(window_seconds=10)
        result = _make_result()
        start = 1000.0
        with patch("pipewatch.alerting.deduplication.time.monotonic", return_value=start):
            dedup.record(result)
        with patch("pipewatch.alerting.deduplication.time.monotonic", return_value=start + 9):
            assert dedup.is_duplicate(result) is True
