"""Tests for pipewatch.metrics."""

import time

import pytest

from pipewatch.metrics import JobMetrics, collect_memory_mb


class TestJobMetrics:
    def _make_metrics(self, name: str = "test_job") -> JobMetrics:
        return JobMetrics(job_name=name)

    def test_elapsed_seconds_none_before_stop(self):
        m = self._make_metrics()
        assert m.elapsed_seconds is None

    def test_elapsed_seconds_after_stop(self):
        m = self._make_metrics()
        time.sleep(0.05)
        m.stop()
        assert m.elapsed_seconds is not None
        assert m.elapsed_seconds >= 0.04

    def test_elapsed_human_in_progress(self):
        m = self._make_metrics()
        assert m.elapsed_human == "in progress"

    def test_elapsed_human_seconds(self):
        m = self._make_metrics()
        m.start_time = 0.0
        m.end_time = 45.3
        assert m.elapsed_human == "45.3s"

    def test_elapsed_human_minutes(self):
        m = self._make_metrics()
        m.start_time = 0.0
        m.end_time = 125.0
        assert m.elapsed_human == "2m 5s"

    def test_elapsed_human_hours(self):
        m = self._make_metrics()
        m.start_time = 0.0
        m.end_time = 3661.0
        assert m.elapsed_human == "1h 1m 1s"

    def test_to_dict_contains_job_name(self):
        m = self._make_metrics("my_pipeline")
        m.stop()
        d = m.to_dict()
        assert d["job_name"] == "my_pipeline"

    def test_to_dict_contains_elapsed(self):
        m = self._make_metrics()
        m.stop()
        d = m.to_dict()
        assert "elapsed_seconds" in d
        assert "elapsed_human" in d

    def test_to_dict_includes_extra(self):
        m = self._make_metrics()
        m.extra = {"source": "s3", "rows": 500}
        m.stop()
        d = m.to_dict()
        assert d["source"] == "s3"
        assert d["rows"] == 500

    def test_records_processed_in_dict(self):
        m = self._make_metrics()
        m.records_processed = 1000
        m.stop()
        d = m.to_dict()
        assert d["records_processed"] == 1000

    def test_peak_memory_mb_in_dict(self):
        m = self._make_metrics()
        m.peak_memory_mb = 128.5
        m.stop()
        d = m.to_dict()
        assert d["peak_memory_mb"] == 128.5


def test_collect_memory_mb_returns_positive_float():
    result = collect_memory_mb()
    assert isinstance(result, float)
    assert result >= 0.0
