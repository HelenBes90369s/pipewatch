"""Alert dispatcher: evaluates rules and dispatches notifications."""
from typing import List, Optional

from pipewatch.alerting.rules import AlertRuleSet, default_rule_set
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


class AlertDispatcher:
    """Evaluates alert rules against a JobResult and fires notifiers."""

    def __init__(
        self,
        notifiers: List[BaseNotifier],
        rule_set: Optional[AlertRuleSet] = None,
    ) -> None:
        self._notifiers = notifiers
        self._rule_set = rule_set or default_rule_set()

    def dispatch(self, result: JobResult) -> dict:
        """Evaluate rules and send alerts. Returns a summary dict."""
        triggered: List[str] = []
        sent: int = 0
        skipped: int = 0

        should_alert = self._should_alert(result)

        if not should_alert:
            return {"triggered": [], "sent": 0, "skipped": len(self._notifiers)}

        for notifier in self._notifiers:
            ok = notifier.send(result)
            if ok:
                sent += 1
                triggered.append(type(notifier).__name__)
            else:
                skipped += 1

        return {"triggered": triggered, "sent": sent, "skipped": skipped}

    def _should_alert(self, result: JobResult) -> bool:
        if result.success and self._rule_set.any_success_alert():
            return True
        if not result.success and self._rule_set.any_failure_alert():
            return True
        if result.metrics and self._rule_set.any_duration_exceeded(
            result.metrics.elapsed_seconds or 0.0
        ):
            return True
        return False
