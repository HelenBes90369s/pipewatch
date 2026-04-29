"""Alerting sub-package for pipewatch."""

from pipewatch.alerting.dispatcher import AlertDispatcher
from pipewatch.alerting.escalation import EscalationLevel, EscalationPolicy
from pipewatch.alerting.escalation_config import build_escalation_policy
from pipewatch.alerting.history_rule import RecoveryAlertRule, StreakAlertRule
from pipewatch.alerting.rules import AlertRule, AlertRuleSet
from pipewatch.alerting.suppression import SuppressionSchedule, SuppressionWindow
from pipewatch.alerting.suppressed_dispatcher import SuppressedAlertDispatcher
from pipewatch.alerting.throttle import AlertThrottle, ThrottleConfig
from pipewatch.alerting.throttled_dispatcher import ThrottledAlertDispatcher

__all__ = [
    "AlertDispatcher",
    "AlertRule",
    "AlertRuleSet",
    "AlertThrottle",
    "EscalationLevel",
    "EscalationPolicy",
    "RecoveryAlertRule",
    "StreakAlertRule",
    "SuppressedAlertDispatcher",
    "SuppressionSchedule",
    "SuppressionWindow",
    "ThrottleConfig",
    "ThrottledAlertDispatcher",
    "build_escalation_policy",
]
