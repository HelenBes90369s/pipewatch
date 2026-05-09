"""Tests for pipewatch.alerting.buffering."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.buffering import AlertBuffer, BufferedAlertDispatcher, BufferConfig
from pipewatch.monitor import JobResult


def _make_result(name: str = "my_job", success: bool = True) -> JobResult:
    return JobResult(
        job_name=name,
        success=success,
        error_message=None if success else "boom",
        duration_seconds=1.5,
    )


def _make_inner() -> MagicMock:
    inner = MagicMock()
    inner.dispatch = MagicMock()
    return inner


# ---------------------------------------------------------------------------
# BufferConfig
# ---------------------------------------------------------------------------

class TestBufferConfig:
    def test_defaults(self):
        cfg = BufferConfig()
        assert cfg.max_size == 10
        assert cfg.max_age_seconds == 60.0

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError, match="max_size"):
            BufferConfig(max_size=0)

    def test_invalid_max_age_raises(self):
        with pytest.raises(ValueError, match="max_age_seconds"):
            BufferConfig(max_age_seconds=0.0)


# ---------------------------------------------------------------------------
# AlertBuffer
# ---------------------------------------------------------------------------

class TestAlertBuffer:
    def _make_buffer(self, max_size=3, max_age=60.0):
        return AlertBuffer(BufferConfig(max_size=max_size, max_age_seconds=max_age))

    def test_empty_on_creation(self):
        buf = self._make_buffer()
        assert buf.is_empty()
        assert buf.size() == 0

    def test_add_increases_size(self):
        buf = self._make_buffer()
        buf.add(_make_result())
        assert buf.size() == 1
        assert not buf.is_empty()

    def test_should_not_flush_when_empty(self):
        buf = self._make_buffer()
        assert not buf.should_flush()

    def test_should_flush_when_max_size_reached(self):
        buf = self._make_buffer(max_size=2)
        buf.add(_make_result())
        assert not buf.should_flush()
        buf.add(_make_result())
        assert buf.should_flush()

    def test_flush_dispatches_all_and_clears(self):
        buf = self._make_buffer(max_size=5)
        inner = _make_inner()
        buf.add(_make_result("job_a"))
        buf.add(_make_result("job_b"))
        flushed = buf.flush(inner)
        assert len(flushed) == 2
        assert inner.dispatch.call_count == 2
        assert buf.is_empty()

    def test_should_flush_when_age_exceeded(self):
        buf = AlertBuffer(BufferConfig(max_size=100, max_age_seconds=0.01))
        buf.add(_make_result())
        time.sleep(0.05)
        assert buf.should_flush()


# ---------------------------------------------------------------------------
# BufferedAlertDispatcher
# ---------------------------------------------------------------------------

class TestBufferedAlertDispatcher:
    def _make_dispatcher(self, max_size=3):
        inner = _make_inner()
        cfg = BufferConfig(max_size=max_size, max_age_seconds=60.0)
        dispatcher = BufferedAlertDispatcher(inner, cfg)
        return dispatcher, inner

    def test_alert_buffered_before_threshold(self):
        dispatcher, inner = self._make_dispatcher(max_size=3)
        dispatcher.dispatch(_make_result())
        dispatcher.dispatch(_make_result())
        inner.dispatch.assert_not_called()
        assert dispatcher.buffer.size() == 2

    def test_flush_on_max_size(self):
        dispatcher, inner = self._make_dispatcher(max_size=2)
        dispatcher.dispatch(_make_result("a"))
        dispatcher.dispatch(_make_result("b"))
        assert inner.dispatch.call_count == 2
        assert dispatcher.buffer.is_empty()

    def test_force_flush(self):
        dispatcher, inner = self._make_dispatcher(max_size=10)
        dispatcher.dispatch(_make_result("x"))
        flushed = dispatcher.flush()
        assert len(flushed) == 1
        inner.dispatch.assert_called_once()

    def test_force_flush_empty_buffer(self):
        dispatcher, inner = self._make_dispatcher()
        flushed = dispatcher.flush()
        assert flushed == []
        inner.dispatch.assert_not_called()

    def test_inner_property(self):
        dispatcher, inner = self._make_dispatcher()
        assert dispatcher.inner is inner
