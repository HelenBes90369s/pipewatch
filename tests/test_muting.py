"""Tests for alert muting (MuteRule, MuteList, MutedAlertDispatcher)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.muting import MuteList, MuteRule, MutedAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(job_name: str = "etl_pipeline", success: bool = True) -> JobResult:
    return JobResult(
        job_name=job_name,
        success=success,
        error_message=None if success else "boom",
        metrics=MagicMock(),
    )


# ---------------------------------------------------------------------------
# MuteRule
# ---------------------------------------------------------------------------

class TestMuteRule:
    def test_exact_match(self):
        rule = MuteRule(pattern="etl_pipeline")
        assert rule.matches(_make_result("etl_pipeline"))

    def test_no_match_different_name(self):
        rule = MuteRule(pattern="etl_pipeline")
        assert not rule.matches(_make_result("other_job"))

    def test_glob_wildcard_matches(self):
        rule = MuteRule(pattern="etl_*")
        assert rule.matches(_make_result("etl_daily"))
        assert rule.matches(_make_result("etl_hourly"))

    def test_glob_wildcard_no_match(self):
        rule = MuteRule(pattern="etl_*")
        assert not rule.matches(_make_result("nightly_sync"))

    def test_reason_stored(self):
        rule = MuteRule(pattern="*", reason="maintenance window")
        assert rule.reason == "maintenance window"


# ---------------------------------------------------------------------------
# MuteList
# ---------------------------------------------------------------------------

class TestMuteList:
    def test_empty_list_never_muted(self):
        ml = MuteList()
        assert not ml.is_muted(_make_result("any_job"))

    def test_matching_rule_mutes(self):
        ml = MuteList()
        ml.add(MuteRule(pattern="etl_pipeline"))
        assert ml.is_muted(_make_result("etl_pipeline"))

    def test_non_matching_rule_does_not_mute(self):
        ml = MuteList()
        ml.add(MuteRule(pattern="other_job"))
        assert not ml.is_muted(_make_result("etl_pipeline"))

    def test_matching_rule_returned(self):
        rule = MuteRule(pattern="etl_*", reason="planned")
        ml = MuteList()
        ml.add(rule)
        assert ml.matching_rule(_make_result("etl_daily")) is rule

    def test_no_matching_rule_returns_none(self):
        ml = MuteList()
        ml.add(MuteRule(pattern="other"))
        assert ml.matching_rule(_make_result("etl_daily")) is None

    def test_rules_property_returns_copy(self):
        ml = MuteList()
        ml.add(MuteRule(pattern="a"))
        rules = ml.rules
        rules.clear()
        assert len(ml.rules) == 1


# ---------------------------------------------------------------------------
# MutedAlertDispatcher
# ---------------------------------------------------------------------------

class TestMutedAlertDispatcher:
    def _make_dispatcher(self, patterns=None):
        inner = MagicMock()
        ml = MuteList()
        for p in (patterns or []):
            ml.add(MuteRule(pattern=p))
        return MutedAlertDispatcher(inner=inner, mute_list=ml), inner

    def test_dispatches_when_not_muted(self):
        dispatcher, inner = self._make_dispatcher()
        result = _make_result("etl_pipeline", success=False)
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once_with(result)

    def test_suppresses_when_muted(self):
        dispatcher, inner = self._make_dispatcher(patterns=["etl_*"])
        result = _make_result("etl_pipeline", success=False)
        dispatcher.dispatch(result)
        inner.dispatch.assert_not_called()

    def test_exposes_mute_list(self):
        dispatcher, _ = self._make_dispatcher()
        assert isinstance(dispatcher.mute_list, MuteList)

    def test_exposes_inner(self):
        dispatcher, inner = self._make_dispatcher()
        assert dispatcher.inner is inner
