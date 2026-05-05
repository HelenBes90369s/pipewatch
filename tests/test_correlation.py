"""Tests for pipewatch.alerting.correlation."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.correlation import (
    AlertCorrelator,
    CorrelationGroup,
    CorrelationWindow,
)
from pipewatch.monitor import JobResult


def _make_result(name: str, success: bool = False, at: datetime | None = None) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = name
    r.success = success
    r.finished_at = at or datetime.utcnow()
    return r


class TestCorrelationWindow:
    def test_contains_within_window(self):
        w = CorrelationWindow(seconds=30)
        anchor = datetime(2024, 1, 1, 12, 0, 0)
        candidate = datetime(2024, 1, 1, 12, 0, 20)
        assert w.contains(anchor, candidate) is True

    def test_not_contains_outside_window(self):
        w = CorrelationWindow(seconds=30)
        anchor = datetime(2024, 1, 1, 12, 0, 0)
        candidate = datetime(2024, 1, 1, 12, 1, 0)
        assert w.contains(anchor, candidate) is False

    def test_exactly_on_boundary(self):
        w = CorrelationWindow(seconds=10)
        anchor = datetime(2024, 1, 1, 12, 0, 0)
        candidate = datetime(2024, 1, 1, 12, 0, 10)
        assert w.contains(anchor, candidate) is True


class TestCorrelationGroup:
    def test_failed_count(self):
        group = CorrelationGroup()
        group.add(_make_result("job-a", success=False))
        group.add(_make_result("job-b", success=True))
        group.add(_make_result("job-c", success=False))
        assert group.failed_count == 2

    def test_job_names(self):
        group = CorrelationGroup()
        group.add(_make_result("alpha"))
        group.add(_make_result("beta"))
        assert group.job_names == ["alpha", "beta"]

    def test_summary_contains_counts_and_names(self):
        group = CorrelationGroup()
        group.add(_make_result("job-x", success=False))
        group.add(_make_result("job-y", success=False))
        summary = group.summary()
        assert "2/2" in summary
        assert "job-x" in summary
        assert "job-y" in summary


class TestAlertCorrelator:
    def test_single_result_creates_one_group(self):
        correlator = AlertCorrelator(CorrelationWindow(seconds=60))
        r = _make_result("job-1", at=datetime(2024, 6, 1, 10, 0, 0))
        correlator.add(r)
        assert len(correlator.groups) == 1

    def test_close_results_grouped_together(self):
        window = CorrelationWindow(seconds=60)
        correlator = AlertCorrelator(window)
        t0 = datetime(2024, 6, 1, 10, 0, 0)
        correlator.add(_make_result("job-a", at=t0))
        correlator.add(_make_result("job-b", at=t0 + timedelta(seconds=30)))
        assert len(correlator.groups) == 1
        assert len(correlator.groups[0].results) == 2

    def test_distant_results_form_separate_groups(self):
        window = CorrelationWindow(seconds=10)
        correlator = AlertCorrelator(window)
        t0 = datetime(2024, 6, 1, 10, 0, 0)
        correlator.add(_make_result("job-a", at=t0))
        correlator.add(_make_result("job-b", at=t0 + timedelta(seconds=60)))
        assert len(correlator.groups) == 2

    def test_flush_clears_groups(self):
        correlator = AlertCorrelator()
        correlator.add(_make_result("job-1"))
        groups = correlator.flush()
        assert len(groups) == 1
        assert len(correlator.groups) == 0

    def test_prune_removes_old_groups(self):
        correlator = AlertCorrelator()
        old_time = datetime.utcnow() - timedelta(minutes=10)
        r = _make_result("old-job", at=old_time)
        group = CorrelationGroup(created_at=old_time)
        group.add(r)
        correlator._groups.append(group)
        correlator.prune(older_than=timedelta(minutes=5))
        assert len(correlator.groups) == 0

    def test_prune_keeps_recent_groups(self):
        correlator = AlertCorrelator()
        correlator.add(_make_result("recent-job"))
        correlator.prune(older_than=timedelta(minutes=5))
        assert len(correlator.groups) == 1
