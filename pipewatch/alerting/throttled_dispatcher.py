"""Alert dispatcher with built-in throttling support."""

from typing import List, Optional

from pipewatch.alerting.dispatcher import AlertDispatcher
from pipewatch.alerting.rules import AlertRuleSet
from pipewatch.alerting.throttle import AlertThrottle, ThrottleConfig
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


class ThrottledAlertDispatcher:
    """Wraps AlertDispatcher with throttle logic to limit notification rate."""

    def __init__(
        self,
        notifiers: List[BaseNotifier],
        rules: Optional[AlertRuleSet] = None,
        throttle_config: Optional[ThrottleConfig] = None,
    ) -> None:
        self._dispatcher = AlertDispatcher(notifiers=notifiers, rules=rules)
        self._throttle = AlertThrottle(config=throttle_config)

    def dispatch(self, result: JobResult) -> bool:
        """Dispatch alert if throttle permits. Returns True if alert was sent."""
        job_name = result.job_name

        if not self._dispatcher._should_alert(result):
            return False

        if not self._throttle.should_send(job_name):
            return False

        sent = self._dispatcher.dispatch(result)
        if sent:
            self._throttle.record(job_name)
        return sent

    @property
    def throttle(self) -> AlertThrottle:
        return self._throttle
