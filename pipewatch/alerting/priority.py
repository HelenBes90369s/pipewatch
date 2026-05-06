"""Alert priority classification and priority-aware dispatching."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from pipewatch.monitor import JobResult


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __ge__(self, other: "Priority") -> bool:
        order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: "Priority") -> bool:
        order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        return order.index(self) > order.index(other)


@dataclass
class PriorityRule:
    """Maps a job name pattern and condition to a priority level."""
    priority: Priority
    job_name: Optional[str] = None          # None means match any
    min_duration_seconds: Optional[float] = None
    on_failure: bool = True
    on_success: bool = False

    def matches(self, result: JobResult) -> bool:
        if self.job_name is not None and result.job_name != self.job_name:
            return False
        if result.success and not self.on_success:
            return False
        if not result.success and not self.on_failure:
            return False
        if self.min_duration_seconds is not None:
            duration = result.metrics.elapsed_seconds() if result.metrics else 0.0
            if duration is None or duration < self.min_duration_seconds:
                return False
        return True


@dataclass
class PriorityClassifier:
    """Classifies a JobResult into a Priority using an ordered list of rules."""
    rules: List[PriorityRule] = field(default_factory=list)
    default_priority: Priority = Priority.MEDIUM

    def classify(self, result: JobResult) -> Priority:
        for rule in self.rules:
            if rule.matches(result):
                return rule.priority
        return self.default_priority
