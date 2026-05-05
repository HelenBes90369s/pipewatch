"""Tests for AlertRouter and RoutingRule."""
import pytest
from unittest.mock import MagicMock

from pipewatch.alerting.routing import AlertRouter, RoutingRule
from pipewatch.monitor import JobResult


def _make_result(job_name: str = "my_job", success: bool = True, tags=None) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = job_name
    r.success = success
    r.tags = tags or []
    return r


class TestRoutingRule:
    def test_matches_exact_name(self):
        rule = RoutingRule(pattern="etl_load", notifier_names=["slack"])
        assert rule.matches(_make_result("etl_load"))

    def test_no_match_different_name(self):
        rule = RoutingRule(pattern="etl_load", notifier_names=["slack"])
        assert not rule.matches(_make_result("other_job"))

    def test_glob_wildcard(self):
        rule = RoutingRule(pattern="etl_*", notifier_names=["slack"])
        assert rule.matches(_make_result("etl_extract"))
        assert rule.matches(_make_result("etl_load"))
        assert not rule.matches(_make_result("reporting_job"))

    def test_tag_filter_passes_when_tag_present(self):
        rule = RoutingRule(pattern="*", notifier_names=["pagerduty"], tags=["critical"])
        assert rule.matches(_make_result(tags=["critical", "nightly"]))

    def test_tag_filter_blocks_when_tag_absent(self):
        rule = RoutingRule(pattern="*", notifier_names=["pagerduty"], tags=["critical"])
        assert not rule.matches(_make_result(tags=["nightly"]))

    def test_no_tags_filter_passes_all(self):
        rule = RoutingRule(pattern="*", notifier_names=["slack"])
        assert rule.matches(_make_result(tags=[]))


class TestAlertRouter:
    def test_first_matching_rule_wins(self):
        r1 = RoutingRule(pattern="etl_*", notifier_names=["slack_ops"])
        r2 = RoutingRule(pattern="*", notifier_names=["slack_general"])
        router = AlertRouter(rules=[r1, r2])
        assert router.resolve(_make_result("etl_load")) == ["slack_ops"]

    def test_fallback_when_no_rule_matches(self):
        router = AlertRouter(rules=[], fallback_notifier_names=["email"])
        assert router.resolve(_make_result("unknown_job")) == ["email"]

    def test_empty_fallback_returns_empty_list(self):
        router = AlertRouter()
        assert router.resolve(_make_result("some_job")) == []

    def test_add_rule_appended(self):
        router = AlertRouter()
        rule = RoutingRule(pattern="*", notifier_names=["slack"])
        router.add_rule(rule)
        assert len(router.rules) == 1
        assert router.resolve(_make_result()) == ["slack"]

    def test_catch_all_pattern(self):
        router = AlertRouter(
            rules=[RoutingRule(pattern="*", notifier_names=["slack"])]
        )
        assert router.resolve(_make_result("anything")) == ["slack"]
