"""Escalation policy: notify additional notifiers after repeated failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.history import JobHistory
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


@dataclass
class EscalationLevel:
    """A single escalation tier triggered after *min_streak* consecutive failures."""

    min_streak: int
    notifiers: List[BaseNotifier] = field(default_factory=list)

    def matches(self, streak: int) -> bool:
        return streak >= self.min_streak


class EscalationPolicy:
    """Dispatches to escalation notifiers when failure streak crosses a threshold."""

    def __init__(self, levels: List[EscalationLevel], history: JobHistory) -> None:
        if not levels:
            raise ValueError("EscalationPolicy requires at least one level.")
        # Sort descending so the highest matching level fires.
        self._levels = sorted(levels, key=lambda l: l.min_streak, reverse=True)
        self._history = history

    def dispatch(self, result: JobResult) -> List[str]:
        """Send escalation notifications if warranted. Returns list of notifier names used."""
        if result.success:
            return []

        entries = self._history.entries(result.job_name)
        streak = sum(1 for _ in _leading_failures(entries))

        fired: List[str] = []
        for level in self._levels:
            if level.matches(streak):
                for notifier in level.notifiers:
                    notifier.send(result)
                    fired.append(type(notifier).__name__)
                break  # Only fire the highest matching level.

        return fired


def _leading_failures(entries):
    """Yield entries from the most-recent end while they are failures."""
    for entry in reversed(entries):
        if not entry.success:
            yield entry
        else:
            break
