"""Tests for pipewatch.alerting.rules."""
import pytest
from pipewatch.alerting.rules import AlertRule, AlertRuleSet, default_rule_set


class TestAlertRule:
    def test_defaults(self):
        rule = AlertRule(name="r")
        assert rule.enabled is True
        assert rule.on_failure is True
        assert rule.on_success is False
        assert rule.max_duration_seconds is None

    def test_should_alert_on_failure_when_enabled(self):
        rule = AlertRule(name="r", on_failure=True)
        assert rule.should_alert_on_failure() is True

    def test_should_not_alert_on_failure_when_disabled(self):
        rule = AlertRule(name="r", enabled=False, on_failure=True)
        assert rule.should_alert_on_failure() is False

    def test_should_alert_on_success(self):
        rule = AlertRule(name="r", on_success=True)
        assert rule.should_alert_on_success() is True

    def test_duration_exceeded_true(self):
        rule = AlertRule(name="r", max_duration_seconds=60.0)
        assert rule.duration_exceeded(90.0) is True

    def test_duration_exceeded_false(self):
        rule = AlertRule(name="r", max_duration_seconds=60.0)
        assert rule.duration_exceeded(30.0) is False

    def test_duration_exceeded_when_none(self):
        rule = AlertRule(name="r", max_duration_seconds=None)
        assert rule.duration_exceeded(9999.0) is False


class TestAlertRuleSet:
    def test_add_returns_self(self):
        rs = AlertRuleSet()
        result = rs.add(AlertRule(name="x"))
        assert result is rs
        assert len(rs.rules) == 1

    def test_any_failure_alert_true(self):
        rs = AlertRuleSet(rules=[AlertRule(name="r", on_failure=True)])
        assert rs.any_failure_alert() is True

    def test_any_failure_alert_false_when_disabled(self):
        rs = AlertRuleSet(rules=[AlertRule(name="r", enabled=False, on_failure=True)])
        assert rs.any_failure_alert() is False

    def test_any_success_alert(self):
        rs = AlertRuleSet(rules=[AlertRule(name="r", on_success=True)])
        assert rs.any_success_alert() is True

    def test_any_duration_exceeded(self):
        rs = AlertRuleSet(rules=[AlertRule(name="r", max_duration_seconds=10.0)])
        assert rs.any_duration_exceeded(20.0) is True
        assert rs.any_duration_exceeded(5.0) is False

    def test_active_rules_filters_disabled(self):
        rs = AlertRuleSet(rules=[
            AlertRule(name="a", enabled=True),
            AlertRule(name="b", enabled=False),
        ])
        assert len(rs.active_rules()) == 1

    def test_default_rule_set_has_failure_alert(self):
        rs = default_rule_set()
        assert rs.any_failure_alert() is True
        assert rs.any_success_alert() is False
