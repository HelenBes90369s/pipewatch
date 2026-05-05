"""Alert correlation: group related alerts from multiple jobs into a single notification."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pipewatch.monitor import JobResult


@dataclass
class CorrelationWindow:
    """Time window within which results are considered correlated."""

    seconds: int = 60

    def contains(self, anchor: datetime, candidate: datetime) -> bool:
        """Return True if candidate falls within the window relative to anchor."""
        delta = abs((candidate - anchor).total_seconds())
        return delta <= self.seconds


@dataclass
class CorrelationGroup:
    """A group of correlated JobResults that share a common failure pattern."""

    results: List[JobResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add(self, result: JobResult) -> None:
        self.results.append(result)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def job_names(self) -> List[str]:
        return [r.job_name for r in self.results]

    def summary(self) -> str:
        names = ", ".join(self.job_names)
        return (
            f"{self.failed_count}/{len(self.results)} jobs failed "
            f"within correlation window: [{names}]"
        )


class AlertCorrelator:
    """Accumulates results and groups them by proximity in time."""

    def __init__(self, window: Optional[CorrelationWindow] = None) -> None:
        self._window = window or CorrelationWindow()
        self._groups: List[CorrelationGroup] = []

    @property
    def groups(self) -> List[CorrelationGroup]:
        return list(self._groups)

    def add(self, result: JobResult) -> CorrelationGroup:
        """Add a result to an existing group or create a new one."""
        ts = result.finished_at or datetime.utcnow()
        for group in reversed(self._groups):
            if self._window.contains(group.created_at, ts):
                group.add(result)
                return group
        new_group = CorrelationGroup(created_at=ts)
        new_group.add(result)
        self._groups.append(new_group)
        return new_group

    def flush(self) -> List[CorrelationGroup]:
        """Return and clear all current groups."""
        groups = self._groups
        self._groups = []
        return groups

    def prune(self, older_than: timedelta) -> None:
        """Remove groups whose window has fully expired."""
        cutoff = datetime.utcnow() - older_than
        self._groups = [g for g in self._groups if g.created_at >= cutoff]
