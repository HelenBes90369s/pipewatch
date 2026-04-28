"""Alert rule that fires when a job has failed N times in a row."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pipewatch.history import JobHistory
from pipewatch.monitor import JobResult


@dataclass
class StreakAlertRule:
    """Trigger an alert after *threshold* consecutive failures."""

    threshold: int = 3
    history: JobHistory = field(default_factory=JobHistory)

    def should_alert(self, result: JobResult) -> bool:
        """Return True when the failure streak meets or exceeds the threshold."""
        if result.success:
            return False
        # Record the current result first so the streak count is up-to-date.
        self.history.record(result)
        streak = self.history.failure_streak(result.job_name)
        return streak >= self.threshold

    def streak_for(self, job_name: str) -> int:
        return self.history.failure_streak(job_name)


@dataclass
class RecoveryAlertRule:
    """Trigger an alert when a job succeeds after one or more failures."""

    min_prior_failures: int = 1
    history: JobHistory = field(default_factory=JobHistory)

    def should_alert(self, result: JobResult) -> bool:
        if not result.success:
            return False
        streak = self.history.failure_streak(result.job_name)
        return streak >= self.min_prior_failures
