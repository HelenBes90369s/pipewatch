"""Tests for CheckpointStore and CheckpointAlertDispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.checkpoint import CheckpointAlertDispatcher, CheckpointStore
from pipewatch.monitor import JobResult


def _make_result(name: str = "etl", success: bool = True, error: str = "") -> JobResult:
    return JobResult(job_name=name, success=success, error_message=error, metrics=None)


# ---------------------------------------------------------------------------
# CheckpointStore
# ---------------------------------------------------------------------------

class TestCheckpointStore:
    def test_last_success_none_for_unknown_job(self):
        store = CheckpointStore()
        assert store.last_success("unknown") is None

    def test_record_and_retrieve(self):
        store = CheckpointStore()
        store.record(_make_result(success=True))
        assert store.last_success("etl") is True

    def test_status_changed_when_unseen(self):
        store = CheckpointStore()
        assert store.status_changed(_make_result()) is True

    def test_status_unchanged_same_outcome(self):
        store = CheckpointStore()
        result = _make_result(success=False)
        store.record(result)
        assert store.status_changed(_make_result(success=False)) is False

    def test_status_changed_on_transition(self):
        store = CheckpointStore()
        store.record(_make_result(success=True))
        assert store.status_changed(_make_result(success=False)) is True

    def test_clear_removes_state(self):
        store = CheckpointStore()
        store.record(_make_result())
        store.clear("etl")
        assert store.last_success("etl") is None

    def test_clear_nonexistent_is_safe(self):
        store = CheckpointStore()
        store.clear("ghost")  # must not raise


# ---------------------------------------------------------------------------
# CheckpointAlertDispatcher
# ---------------------------------------------------------------------------

class TestCheckpointAlertDispatcher:
    def _make(self):
        inner = MagicMock()
        dispatcher = CheckpointAlertDispatcher(inner=inner)
        return dispatcher, inner

    def test_alert_sent_on_first_occurrence(self):
        dispatcher, inner = self._make()
        result = _make_result(success=False)
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once_with(result)

    def test_no_alert_on_repeated_failure(self):
        dispatcher, inner = self._make()
        dispatcher.dispatch(_make_result(success=False))
        dispatcher.dispatch(_make_result(success=False))
        assert inner.dispatch.call_count == 1

    def test_alert_sent_on_recovery(self):
        dispatcher, inner = self._make()
        dispatcher.dispatch(_make_result(success=False))
        dispatcher.dispatch(_make_result(success=True))
        assert inner.dispatch.call_count == 2

    def test_no_alert_on_repeated_success(self):
        dispatcher, inner = self._make()
        dispatcher.dispatch(_make_result(success=True))
        dispatcher.dispatch(_make_result(success=True))
        assert inner.dispatch.call_count == 1

    def test_state_recorded_after_dispatch(self):
        dispatcher, _ = self._make()
        dispatcher.dispatch(_make_result(success=True))
        assert dispatcher.store.last_success("etl") is True

    def test_inner_property(self):
        inner = MagicMock()
        dispatcher = CheckpointAlertDispatcher(inner=inner)
        assert dispatcher.inner is inner

    def test_custom_store_used(self):
        store = CheckpointStore()
        store.record(_make_result(success=False))
        inner = MagicMock()
        dispatcher = CheckpointAlertDispatcher(inner=inner, store=store)
        # Same failure again — should NOT alert
        dispatcher.dispatch(_make_result(success=False))
        inner.dispatch.assert_not_called()
