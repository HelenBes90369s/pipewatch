"""Tests for PipelineMonitor and the watch context manager."""

import pytest
from unittest.mock import MagicMock, patch

from pipewatch.monitor import PipelineMonitor, JobResult
from pipewatch.context import watch
from pipewatch.config import PipewatchConfig, SlackConfig, EmailConfig


def _config_no_notifiers() -> PipewatchConfig:
    return PipewatchConfig(slack=SlackConfig(), email=EmailConfig())


class TestPipelineMonitor:
    def test_finish_without_start_raises(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        with pytest.raises(RuntimeError, match="start()"):
            monitor.finish()

    def test_successful_job_returns_result(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        monitor.start()
        result = monitor.finish(success=True)
        assert isinstance(result, JobResult)
        assert result.success is True
        assert result.name == "test-job"
        assert result.duration_seconds >= 0
        assert result.error_message is None

    def test_failed_job_stores_error_message(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        monitor.start()
        result = monitor.finish(success=False, error_message="Something went wrong")
        assert result.success is False
        assert result.error_message == "Something went wrong"

    def test_alert_called_on_failure(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        monitor._alert = MagicMock()
        monitor.start()
        monitor.finish(success=False, error_message="boom")
        monitor._alert.assert_called_once()

    def test_alert_not_called_on_success(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        monitor._alert = MagicMock()
        monitor.start()
        monitor.finish(success=True)
        monitor._alert.assert_not_called()

    def test_no_notifiers_built_without_config(self):
        monitor = PipelineMonitor("test-job", config=_config_no_notifiers())
        assert monitor._notifiers == []


class TestWatchContextManager:
    def test_success_path(self):
        with watch("ctx-job", config=_config_no_notifiers()) as job:
            pass
        assert job.result is not None
        assert job.result.success is True
        assert job.result.name == "ctx-job"

    def test_exception_marks_failure(self):
        with pytest.raises(ValueError):
            with watch("ctx-job", config=_config_no_notifiers()) as job:
                raise ValueError("pipeline error")
        assert job.result.success is False
        assert "ValueError" in job.result.error_message
        assert "pipeline error" in job.result.error_message

    def test_exception_is_not_suppressed(self):
        with pytest.raises(RuntimeError):
            with watch("ctx-job", config=_config_no_notifiers()):
                raise RuntimeError("do not swallow")

    def test_result_has_duration(self):
        with watch("ctx-job", config=_config_no_notifiers()) as job:
            pass
        assert job.result.duration_seconds >= 0
