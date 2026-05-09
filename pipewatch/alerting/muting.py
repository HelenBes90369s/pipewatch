"""Alert muting: silence alerts for specific jobs or patterns."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.monitor import JobResult


@dataclass
class MuteRule:
    """A single rule that silences alerts matching a job name pattern."""

    pattern: str
    reason: str = ""

    def matches(self, result: JobResult) -> bool:
        """Return True if the job name matches this mute rule's pattern."""
        return fnmatch.fnmatch(result.job_name, self.pattern)


@dataclass
class MuteList:
    """Collection of mute rules checked before dispatching alerts."""

    _rules: List[MuteRule] = field(default_factory=list)

    def add(self, rule: MuteRule) -> None:
        """Register a new mute rule."""
        self._rules.append(rule)

    def remove(self, pattern: str) -> bool:
        """Remove all rules with the given pattern.

        Returns True if at least one rule was removed, False otherwise.
        """
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.pattern != pattern]
        return len(self._rules) < before

    def is_muted(self, result: JobResult) -> bool:
        """Return True if any rule matches the given result."""
        return any(rule.matches(result) for rule in self._rules)

    def matching_rule(self, result: JobResult) -> Optional[MuteRule]:
        """Return the first matching rule, or None."""
        for rule in self._rules:
            if rule.matches(result):
                return rule
        return None

    @property
    def rules(self) -> List[MuteRule]:
        return list(self._rules)


class MutedAlertDispatcher:
    """Wraps an inner dispatcher and skips alerts for muted jobs."""

    def __init__(self, inner, mute_list: MuteList) -> None:
        self._inner = inner
        self._mute_list = mute_list

    def dispatch(self, result: JobResult) -> None:
        if self._mute_list.is_muted(result):
            return
        self._inner.dispatch(result)

    @property
    def mute_list(self) -> MuteList:
        return self._mute_list

    @property
    def inner(self):
        return self._inner
