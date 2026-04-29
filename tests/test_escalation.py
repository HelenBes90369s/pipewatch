"""Tests for EscalationPolicy and EscalationLevel."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.escalation import EscalationLevel, EscalationPolicy
from pipewatch.history import HistoryEntry, JobHistory
from pipewatch.monitor import JobResult


def _make_result(job_name: str = "etl", success: bool = False) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = job_name
    r.success = success
    r.error = None if success else "boom"
    return r


def _make_history(job_name: str, successes: list[bool]) -> JobHistory:
    history = JobHistory()
    for ok in successes:
        entry = MagicMock(spec=HistoryEntry)
        entry.success = ok
        history._records.setdefault(job_name, []).append(entry)
    return history


def _make_notifier():
    n = MagicMock()
    n.send = MagicMock(return_value=True)
    return n


class TestEscalationLevel:
    def test_matches_at_threshold(self):
        level = EscalationLevel(min_streak=3)
        assert level.matches(3) is True

    def test_matches_above_threshold(self):
        level = EscalationLevel(min_streak=3)
        assert level.matches(5) is True

    def test_no_match_below_threshold(self):
        level = EscalationLevel(min_streak=3)
        assert level.matches(2) is False


class TestEscalationPolicy:
    def test_no_dispatch_on_success(self):
        notifier = _make_notifier()
        history = _make_history("etl", [True, True])
        policy = EscalationPolicy(
            levels=[EscalationLevel(min_streak=1, notifiers=[notifier])],
            history=history,
        )
        fired = policy.dispatch(_make_result(success=True))
        assert fired == []
        notifier.send.assert_not_called()

    def test_no_dispatch_below_streak(self):
        notifier = _make_notifier()
        history = _make_history("etl", [True, False])  # streak of 1
        policy = EscalationPolicy(
            levels=[EscalationLevel(min_streak=3, notifiers=[notifier])],
            history=history,
        )
        fired = policy.dispatch(_make_result())
        assert fired == []
        notifier.send.assert_not_called()

    def test_dispatches_at_streak_threshold(self):
        notifier = _make_notifier()
        history = _make_history("etl", [False, False, False])  # streak of 3
        policy = EscalationPolicy(
            levels=[EscalationLevel(min_streak=3, notifiers=[notifier])],
            history=history,
        )
        result = _make_result()
        fired = policy.dispatch(result)
        assert len(fired) == 1
        notifier.send.assert_called_once_with(result)

    def test_highest_level_wins(self):
        low_notifier = _make_notifier()
        high_notifier = _make_notifier()
        history = _make_history("etl", [False, False, False, False, False])  # streak 5
        policy = EscalationPolicy(
            levels=[
                EscalationLevel(min_streak=2, notifiers=[low_notifier]),
                EscalationLevel(min_streak=5, notifiers=[high_notifier]),
            ],
            history=history,
        )
        policy.dispatch(_make_result())
        high_notifier.send.assert_called_once()
        low_notifier.send.assert_not_called()

    def test_empty_levels_raises(self):
        with pytest.raises(ValueError):
            EscalationPolicy(levels=[], history=JobHistory())
