"""Alert routing — direct alerts to different notifiers based on job tags or names."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Optional

from pipewatch.monitor import JobResult


@dataclass
class RoutingRule:
    """Maps a pattern (glob against job name) to a list of notifier names."""

    pattern: str
    notifier_names: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def matches(self, result: JobResult) -> bool:
        """Return True when the rule applies to *result*."""
        name_match = fnmatch(result.job_name, self.pattern)
        if not name_match:
            return False
        if self.tags:
            job_tags = getattr(result, "tags", []) or []
            return any(t in job_tags for t in self.tags)
        return True


class AlertRouter:
    """Choose which notifiers should receive an alert for a given job result."""

    def __init__(
        self,
        rules: Optional[List[RoutingRule]] = None,
        fallback_notifier_names: Optional[List[str]] = None,
    ) -> None:
        self._rules: List[RoutingRule] = rules or []
        self._fallback: List[str] = fallback_notifier_names or []

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule)

    def resolve(self, result: JobResult) -> List[str]:
        """Return the list of notifier names that should be alerted."""
        for rule in self._rules:
            if rule.matches(result):
                return list(rule.notifier_names)
        return list(self._fallback)

    @property
    def rules(self) -> List[RoutingRule]:
        return list(self._rules)
