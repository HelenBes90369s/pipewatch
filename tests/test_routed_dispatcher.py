"""Tests for RoutedAlertDispatcher."""
from unittest.mock import MagicMock, patch

from pipewatch.alerting.routing import AlertRouter, RoutingRule
from pipewatch.alerting.routed_dispatcher import RoutedAlertDispatcher
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


def _make_result(job_name: str = "etl_load", success: bool = False) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = job_name
    r.success = success
    r.tags = []
    return r


def _make_notifier(name: str = "slack") -> BaseNotifier:
    n = MagicMock(spec=BaseNotifier)
    n.name = name
    return n


class TestRoutedAlertDispatcher:
    def _make_dispatcher(self, rules=None, fallback=None, notifiers=None):
        router = AlertRouter(rules=rules or [], fallback_notifier_names=fallback or [])
        return RoutedAlertDispatcher(router=router, notifiers=notifiers or {})

    def test_routes_to_correct_notifier(self):
        notifier = _make_notifier("slack_ops")
        rule = RoutingRule(pattern="etl_*", notifier_names=["slack_ops"])
        dispatcher = self._make_dispatcher(rules=[rule], notifiers={"slack_ops": notifier})

        with patch("pipewatch.alerting.routed_dispatcher.AlertDispatcher") as MockDisp:
            instance = MockDisp.return_value
            dispatcher.dispatch(_make_result("etl_load"))
            MockDisp.assert_called_once_with(notifiers=[notifier])
            instance.dispatch.assert_called_once()

    def test_unknown_notifier_name_skipped(self):
        rule = RoutingRule(pattern="*", notifier_names=["does_not_exist"])
        dispatcher = self._make_dispatcher(rules=[rule], notifiers={})
        with patch("pipewatch.alerting.routed_dispatcher.AlertDispatcher") as MockDisp:
            dispatcher.dispatch(_make_result())
            MockDisp.assert_not_called()

    def test_no_matching_rule_no_dispatch(self):
        dispatcher = self._make_dispatcher()
        with patch("pipewatch.alerting.routed_dispatcher.AlertDispatcher") as MockDisp:
            dispatcher.dispatch(_make_result())
            MockDisp.assert_not_called()

    def test_fallback_notifier_used_when_no_rule_matches(self):
        notifier = _make_notifier("email")
        dispatcher = self._make_dispatcher(
            fallback=["email"], notifiers={"email": notifier}
        )
        with patch("pipewatch.alerting.routed_dispatcher.AlertDispatcher") as MockDisp:
            instance = MockDisp.return_value
            dispatcher.dispatch(_make_result())
            MockDisp.assert_called_once_with(notifiers=[notifier])
            instance.dispatch.assert_called_once()

    def test_router_property(self):
        router = AlertRouter()
        dispatcher = RoutedAlertDispatcher(router=router, notifiers={})
        assert dispatcher.router is router

    def test_notifiers_property_returns_copy(self):
        n = _make_notifier()
        dispatcher = RoutedAlertDispatcher(
            router=AlertRouter(), notifiers={"slack": n}
        )
        copy = dispatcher.notifiers
        assert copy == {"slack": n}
        copy["extra"] = _make_notifier("extra")
        assert "extra" not in dispatcher.notifiers
