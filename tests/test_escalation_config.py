"""Tests for build_escalation_policy helper."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.escalation import EscalationPolicy
from pipewatch.alerting.escalation_config import build_escalation_policy
from pipewatch.history import JobHistory


def _make_notifier(name: str = "slack"):
    n = MagicMock()
    n.__class__.__name__ = name
    return n


class TestBuildEscalationPolicy:
    def test_builds_single_level(self):
        slack = _make_notifier("SlackNotifier")
        cfg = [{"min_streak": 3, "notifiers": ["slack"]}]
        policy = build_escalation_policy(cfg, {"slack": slack}, JobHistory())
        assert isinstance(policy, EscalationPolicy)

    def test_unknown_notifier_name_skipped(self):
        cfg = [{"min_streak": 2, "notifiers": ["unknown"]}]
        # Should not raise; unknown names are silently skipped.
        policy = build_escalation_policy(cfg, {}, JobHistory())
        assert isinstance(policy, EscalationPolicy)

    def test_multiple_levels(self):
        slack = _make_notifier()
        email = _make_notifier()
        cfg = [
            {"min_streak": 2, "notifiers": ["slack"]},
            {"min_streak": 5, "notifiers": ["slack", "email"]},
        ]
        policy = build_escalation_policy(
            cfg, {"slack": slack, "email": email}, JobHistory()
        )
        assert isinstance(policy, EscalationPolicy)
        assert len(policy._levels) == 2

    def test_empty_cfg_raises(self):
        with pytest.raises(ValueError):
            build_escalation_policy([], {}, JobHistory())

    def test_default_min_streak_is_one(self):
        notifier = _make_notifier()
        cfg = [{"notifiers": ["slack"]}]  # no min_streak key
        policy = build_escalation_policy(cfg, {"slack": notifier}, JobHistory())
        assert policy._levels[0].min_streak == 1
