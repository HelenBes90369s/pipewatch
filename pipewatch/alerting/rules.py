"""Alert rule definitions for pipewatch pipeline monitoring."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AlertRule:
    """Defines conditions under which an alert should be triggered."""

    name: str
    enabled: bool = True
    # Trigger alert if job duration exceeds this many seconds
    max_duration_seconds: Optional[float] = None
    # Trigger alert on job failure
    on_failure: bool = True
    # Trigger alert on job success
    on_success: bool = False
    # Only alert if retry attempts exhausted (for retrying notifiers)
    only_on_final_failure: bool = False

    def should_alert_on_failure(self) -> bool:
        return self.enabled and self.on_failure

    def should_alert_on_success(self) -> bool:
        return self.enabled and self.on_success

    def duration_exceeded(self, elapsed_seconds: float) -> bool:
        if not self.enabled or self.max_duration_seconds is None:
            return False
        return elapsed_seconds > self.max_duration_seconds


@dataclass
class AlertRuleSet:
    """Collection of alert rules applied to a monitored pipeline job."""

    rules: list = field(default_factory=list)

    def add(self, rule: AlertRule) -> "AlertRuleSet":
        self.rules.append(rule)
        return self

    def any_failure_alert(self) -> bool:
        return any(r.should_alert_on_failure() for r in self.rules)

    def any_success_alert(self) -> bool:
        return any(r.should_alert_on_success() for r in self.rules)

    def any_duration_exceeded(self, elapsed_seconds: float) -> bool:
        return any(r.duration_exceeded(elapsed_seconds) for r in self.rules)

    def active_rules(self) -> list:
        return [r for r in self.rules if r.enabled]


def default_rule_set() -> AlertRuleSet:
    """Returns a sensible default rule set for most pipeline jobs."""
    return AlertRuleSet(rules=[
        AlertRule(name="default", on_failure=True, on_success=False)
    ])
