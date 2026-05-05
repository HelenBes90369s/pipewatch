"""Tests for AlertAggregator and AggregatedAlertDispatcher."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.aggregation import AggregatedBatch, AggregationConfig, AlertAggregator
from pipewatch.alerting.aggregated_dispatcher import AggregatedAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(name: str = "job", success: bool = True, error: str = "") -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = name
    r.success = success
    r.error_message = error
    r.metrics = None
    return r


def _make_notifier(returns: bool = True) -> MagicMock:
    n = MagicMock()
    n.send.return_value = returns
    return n


# ---------------------------------------------------------------------------
# AggregationConfig
# ---------------------------------------------------------------------------

class TestAggregationConfig:
    def test_defaults(self):
        cfg = AggregationConfig()
        assert cfg.max_size == 10
        assert cfg.max_age_seconds == 300.0
        assert cfg.only_failures is False

    def test_custom_values(self):
        cfg = AggregationConfig(max_size=3, max_age_seconds=60.0, only_failures=True)
        assert cfg.max_size == 3
        assert cfg.only_failures is True


# ---------------------------------------------------------------------------
# AggregatedBatch
# ---------------------------------------------------------------------------

class TestAggregatedBatch:
    def test_empty_on_creation(self):
        batch = AggregatedBatch()
        assert batch.is_empty()

    def test_add_increases_count(self):
        batch = AggregatedBatch()
        batch.add(_make_result())
        assert len(batch.results) == 1
        assert not batch.is_empty()

    def test_failure_and_success_counts(self):
        batch = AggregatedBatch()
        batch.add(_make_result(success=True))
        batch.add(_make_result(success=False))
        batch.add(_make_result(success=False))
        assert batch.success_count() == 1
        assert batch.failure_count() == 2

    def test_age_seconds(self):
        past = datetime.utcnow() - timedelta(seconds=10)
        batch = AggregatedBatch(created_at=past)
        assert batch.age_seconds() >= 10.0

    def test_summary_contains_counts(self):
        batch = AggregatedBatch()
        batch.add(_make_result(success=True))
        batch.add(_make_result(success=False))
        summary = batch.summary()
        assert "2 job" in summary
        assert "1 succeeded" in summary
        assert "1 failed" in summary


# ---------------------------------------------------------------------------
# AlertAggregator
# ---------------------------------------------------------------------------

class TestAlertAggregator:
    def test_no_flush_below_max_size(self):
        agg = AlertAggregator(AggregationConfig(max_size=3))
        assert agg.add(_make_result()) is None
        assert agg.add(_make_result()) is None
        assert agg.pending_count() == 2

    def test_flush_at_max_size(self):
        agg = AlertAggregator(AggregationConfig(max_size=2))
        agg.add(_make_result())
        batch = agg.add(_make_result())
        assert batch is not None
        assert len(batch.results) == 2
        assert agg.pending_count() == 0

    def test_manual_flush_returns_batch(self):
        agg = AlertAggregator(AggregationConfig(max_size=10))
        agg.add(_make_result())
        batch = agg.flush()
        assert batch is not None
        assert len(batch.results) == 1

    def test_manual_flush_empty_returns_none(self):
        agg = AlertAggregator()
        assert agg.flush() is None

    def test_only_failures_skips_successes(self):
        agg = AlertAggregator(AggregationConfig(max_size=1, only_failures=True))
        result = agg.add(_make_result(success=True))
        assert result is None
        assert agg.pending_count() == 0

    def test_only_failures_includes_failures(self):
        agg = AlertAggregator(AggregationConfig(max_size=1, only_failures=True))
        batch = agg.add(_make_result(success=False))
        assert batch is not None


# ---------------------------------------------------------------------------
# AggregatedAlertDispatcher
# ---------------------------------------------------------------------------

class TestAggregatedAlertDispatcher:
    def _make_dispatcher(self, max_size=2, notifier=None):
        n = notifier or _make_notifier()
        cfg = AggregationConfig(max_size=max_size)
        return AggregatedAlertDispatcher([n], cfg), n

    def test_no_send_below_threshold(self):
        dispatcher, notifier = self._make_dispatcher(max_size=3)
        assert dispatcher.dispatch(_make_result()) is False
        notifier.send.assert_not_called()

    def test_send_when_threshold_reached(self):
        dispatcher, notifier = self._make_dispatcher(max_size=2)
        dispatcher.dispatch(_make_result())
        result = dispatcher.dispatch(_make_result())
        assert result is True
        notifier.send.assert_called_once()

    def test_flush_sends_pending(self):
        dispatcher, notifier = self._make_dispatcher(max_size=10)
        dispatcher.dispatch(_make_result())
        result = dispatcher.flush()
        assert result is True
        notifier.send.assert_called_once()

    def test_flush_empty_returns_false(self):
        dispatcher, notifier = self._make_dispatcher()
        assert dispatcher.flush() is False
        notifier.send.assert_not_called()

    def test_message_contains_job_name(self):
        dispatcher, notifier = self._make_dispatcher(max_size=1)
        dispatcher.dispatch(_make_result(name="my_pipeline", success=False, error="timeout"))
        message = notifier.send.call_args[0][0]
        assert "my_pipeline" in message
        assert "timeout" in message
