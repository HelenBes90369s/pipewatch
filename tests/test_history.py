"""Tests for pipewatch.history."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipewatch.history import HistoryEntry, JobHistory
from pipewatch.monitor import JobResult


def _make_result(job_name="etl", success=True, error=None):
    metrics = MagicMock()
    metrics.started_at = None
    metrics.elapsed_seconds.return_value = 12.5
    return JobResult(
        job_name=job_name,
        success=success,
        metrics=metrics,
        error_message=error,
    )


class TestHistoryEntry:
    def test_from_result_success(self):
        r = _make_result(success=True)
        entry = HistoryEntry.from_result(r)
        assert entry.job_name == "etl"
        assert entry.success is True
        assert entry.elapsed_seconds == 12.5
        assert entry.error_message is None

    def test_from_result_failure(self):
        r = _make_result(success=False, error="timeout")
        entry = HistoryEntry.from_result(r)
        assert entry.success is False
        assert entry.error_message == "timeout"

    def test_to_dict_keys(self):
        r = _make_result()
        d = HistoryEntry.from_result(r).to_dict()
        assert set(d.keys()) == {
            "job_name", "success", "started_at", "elapsed_seconds", "error_message"
        }


class TestJobHistory:
    def test_record_creates_file(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result())
        assert path.exists()

    def test_record_and_load(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result(job_name="job_a", success=True))
        h.record(_make_result(job_name="job_b", success=False))
        all_entries = h.load()
        assert len(all_entries) == 2

    def test_load_filter_by_name(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result(job_name="job_a"))
        h.record(_make_result(job_name="job_b"))
        entries = h.load(job_name="job_a")
        assert len(entries) == 1
        assert entries[0].job_name == "job_a"

    def test_load_empty_when_no_file(self, tmp_path):
        h = JobHistory(tmp_path / "missing.jsonl")
        assert h.load() == []

    def test_last_returns_most_recent(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result(success=True))
        h.record(_make_result(success=False, error="boom"))
        last = h.last("etl")
        assert last is not None
        assert last.success is False

    def test_last_returns_none_for_unknown_job(self, tmp_path):
        h = JobHistory(tmp_path / "hist.jsonl")
        assert h.last("unknown") is None

    def test_failure_streak_consecutive(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result(success=True))
        h.record(_make_result(success=False))
        h.record(_make_result(success=False))
        assert h.failure_streak("etl") == 2

    def test_failure_streak_reset_by_success(self, tmp_path):
        path = tmp_path / "hist.jsonl"
        h = JobHistory(path)
        h.record(_make_result(success=False))
        h.record(_make_result(success=False))
        h.record(_make_result(success=True))
        assert h.failure_streak("etl") == 0
