"""Tests for pipewatch.alerting.digest."""

from unittest.mock import MagicMock
from datetime import datetime

from pipewatch.alerting.digest import AlertDigest, DigestEntry


def _make_result(job_name="pipeline", success=True, elapsed_human="1m 2s", error=None):
    result = MagicMock()
    result.job_name = job_name
    result.success = success
    result.error_message = error
    result.metrics.elapsed_human.return_value = elapsed_human
    return result


class TestDigestEntry:
    def test_from_result_success(self):
        result = _make_result(job_name="etl", success=True, elapsed_human="30s")
        entry = DigestEntry.from_result(result)
        assert entry.job_name == "etl"
        assert entry.success is True
        assert entry.elapsed_human == "30s"
        assert entry.error_message is None

    def test_from_result_failure(self):
        result = _make_result(success=False, error="timeout")
        entry = DigestEntry.from_result(result)
        assert entry.success is False
        assert entry.error_message == "timeout"

    def test_summary_line_success(self):
        entry = DigestEntry(job_name="load", success=True, elapsed_human="5s")
        line = entry.summary_line()
        assert "✅" in line
        assert "load" in line
        assert "5s" in line

    def test_summary_line_failure_includes_error(self):
        entry = DigestEntry(job_name="transform", success=False,
                            elapsed_human="2m", error_message="OOM")
        line = entry.summary_line()
        assert "❌" in line
        assert "OOM" in line


class TestAlertDigest:
    def test_is_empty_initially(self):
        digest = AlertDigest()
        assert digest.is_empty()

    def test_add_increases_entry_count(self):
        digest = AlertDigest()
        digest.add(_make_result())
        assert len(digest.entries) == 1
        assert not digest.is_empty()

    def test_failure_and_success_counts(self):
        digest = AlertDigest()
        digest.add(_make_result(success=True))
        digest.add(_make_result(success=True))
        digest.add(_make_result(success=False, error="err"))
        assert digest.success_count() == 2
        assert digest.failure_count() == 1

    def test_render_text_includes_header(self):
        digest = AlertDigest()
        digest.add(_make_result(job_name="ingest", success=True))
        text = digest.render_text()
        assert "Pipeline Digest" in text
        assert "ingest" in text

    def test_render_text_empty(self):
        digest = AlertDigest()
        text = digest.render_text()
        assert "No jobs" in text

    def test_flush_calls_notifiers_and_clears(self):
        digest = AlertDigest()
        digest.add(_make_result())
        notifier = MagicMock()
        digest.flush([notifier])
        notifier.send.assert_called_once()
        assert digest.is_empty()

    def test_flush_does_nothing_when_empty(self):
        digest = AlertDigest()
        notifier = MagicMock()
        digest.flush([notifier])
        notifier.send.assert_not_called()

    def test_flush_resets_created_at(self):
        digest = AlertDigest()
        original_time = digest.created_at
        digest.add(_make_result())
        digest.flush([])
        assert digest.created_at >= original_time
