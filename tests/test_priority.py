"""Tests for priority classification and priority-aware dispatching."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.priority import Priority, PriorityClassifier, PriorityRule
from pipewatch.alerting.priority_dispatcher import PriorityAlertDispatcher
from pipewatch.alerting.priority_config import build_priority_dispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(name: str = "job", success: bool = False, duration: float = 0.0):
    metrics = MagicMock()
    metrics.elapsed_seconds.return_value = duration
    result = MagicMock()
    result.job_name = name
    result.success = success
    result.metrics = metrics
    return result


def _make_notifier():
    n = MagicMock()
    n.send = MagicMock()
    return n


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_critical_ge_high(self):
        assert Priority.CRITICAL >= Priority.HIGH

    def test_low_not_ge_medium(self):
        assert not (Priority.LOW >= Priority.MEDIUM)

    def test_equal_priorities(self):
        assert Priority.HIGH >= Priority.HIGH


# ---------------------------------------------------------------------------
# PriorityRule.matches
# ---------------------------------------------------------------------------

class TestPriorityRule:
    def test_matches_any_job_when_no_name(self):
        rule = PriorityRule(priority=Priority.HIGH)
        assert rule.matches(_make_result(name="anything", success=False))

    def test_no_match_wrong_job_name(self):
        rule = PriorityRule(priority=Priority.HIGH, job_name="etl")
        assert not rule.matches(_make_result(name="other", success=False))

    def test_no_match_success_when_only_failure(self):
        rule = PriorityRule(priority=Priority.HIGH, on_failure=True, on_success=False)
        assert not rule.matches(_make_result(success=True))

    def test_matches_success_when_enabled(self):
        rule = PriorityRule(priority=Priority.LOW, on_failure=False, on_success=True)
        assert rule.matches(_make_result(success=True))

    def test_min_duration_not_met(self):
        rule = PriorityRule(priority=Priority.CRITICAL, min_duration_seconds=60.0)
        assert not rule.matches(_make_result(duration=30.0))

    def test_min_duration_met(self):
        rule = PriorityRule(priority=Priority.CRITICAL, min_duration_seconds=60.0)
        assert rule.matches(_make_result(duration=90.0))


# ---------------------------------------------------------------------------
# PriorityClassifier
# ---------------------------------------------------------------------------

class TestPriorityClassifier:
    def test_returns_default_when_no_rules(self):
        clf = PriorityClassifier(default_priority=Priority.LOW)
        assert clf.classify(_make_result()) == Priority.LOW

    def test_first_matching_rule_wins(self):
        rules = [
            PriorityRule(priority=Priority.CRITICAL, job_name="etl"),
            PriorityRule(priority=Priority.LOW),
        ]
        clf = PriorityClassifier(rules=rules)
        assert clf.classify(_make_result(name="etl")) == Priority.CRITICAL

    def test_falls_through_to_second_rule(self):
        rules = [
            PriorityRule(priority=Priority.CRITICAL, job_name="etl"),
            PriorityRule(priority=Priority.LOW),
        ]
        clf = PriorityClassifier(rules=rules)
        assert clf.classify(_make_result(name="other")) == Priority.LOW


# ---------------------------------------------------------------------------
# PriorityAlertDispatcher
# ---------------------------------------------------------------------------

class TestPriorityAlertDispatcher:
    def _make_dispatcher(self, exact_match: bool = False) -> PriorityAlertDispatcher:
        clf = PriorityClassifier(default_priority=Priority.HIGH)
        return PriorityAlertDispatcher(classifier=clf, exact_match=exact_match)

    def test_notifier_called_for_matching_priority(self):
        dispatcher = self._make_dispatcher()
        notifier = _make_notifier()
        dispatcher.register(notifier, Priority.HIGH)
        result = _make_result()
        dispatcher.dispatch(result)
        notifier.send.assert_called_once_with(result)

    def test_notifier_called_for_higher_priority(self):
        """A notifier registered for LOW should also fire on HIGH alerts."""
        dispatcher = self._make_dispatcher()  # default HIGH
        notifier = _make_notifier()
        dispatcher.register(notifier, Priority.LOW)
        dispatcher.dispatch(_make_result())
        notifier.send.assert_called_once()

    def test_notifier_not_called_for_lower_priority(self):
        """A notifier registered for CRITICAL should NOT fire on HIGH alerts."""
        dispatcher = self._make_dispatcher()  # default HIGH
        notifier = _make_notifier()
        dispatcher.register(notifier, Priority.CRITICAL)
        dispatcher.dispatch(_make_result())
        notifier.send.assert_not_called()

    def test_exact_match_only_fires_exact_priority(self):
        dispatcher = self._make_dispatcher(exact_match=True)  # default HIGH
        low_notifier = _make_notifier()
        high_notifier = _make_notifier()
        dispatcher.register(low_notifier, Priority.LOW)
        dispatcher.register(high_notifier, Priority.HIGH)
        dispatcher.dispatch(_make_result())
        low_notifier.send.assert_not_called()
        high_notifier.send.assert_called_once()


# ---------------------------------------------------------------------------
# build_priority_dispatcher
# ---------------------------------------------------------------------------

class TestBuildPriorityDispatcher:
    def test_builds_with_named_notifier(self):
        notifier = _make_notifier()
        dispatcher = build_priority_dispatcher(
            rules_cfg=[{"priority": "critical", "job_name": "etl"}],
            notifiers_cfg=[{"name": "slack", "priority": "high"}],
            named_notifiers={"slack": notifier},
        )
        assert isinstance(dispatcher, PriorityAlertDispatcher)

    def test_unknown_notifier_name_skipped(self):
        dispatcher = build_priority_dispatcher(
            rules_cfg=[],
            notifiers_cfg=[{"name": "missing", "priority": "high"}],
            named_notifiers={},
        )
        # Should not raise; dispatcher has no notifiers registered
        dispatcher.dispatch(_make_result())

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError, match="Unknown priority"):
            build_priority_dispatcher(
                rules_cfg=[{"priority": "ultra"}],
                notifiers_cfg=[],
                named_notifiers={},
            )
