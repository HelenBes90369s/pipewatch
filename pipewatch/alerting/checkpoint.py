"""Checkpoint-based alerting: only alert when a job's status changes from its last known state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewatch.monitor import JobResult


@dataclass
class CheckpointStore:
    """Tracks the last known outcome (success/failure) for each job."""

    _states: Dict[str, bool] = field(default_factory=dict)

    def last_success(self, job_name: str) -> Optional[bool]:
        """Return the last recorded success state, or None if unseen."""
        return self._states.get(job_name)

    def record(self, result: JobResult) -> None:
        """Persist the outcome of *result* so future calls can compare."""
        self._states[result.job_name] = result.success

    def status_changed(self, result: JobResult) -> bool:
        """Return True if the job's outcome differs from the stored state."""
        last = self.last_success(result.job_name)
        if last is None:
            return True
        return last != result.success

    def clear(self, job_name: str) -> None:
        """Remove the stored state for *job_name*."""
        self._states.pop(job_name, None)


class CheckpointAlertDispatcher:
    """Wraps an inner dispatcher and only forwards alerts on status change.

    This prevents repeated alerts for jobs that are consistently failing or
    consistently succeeding — only transitions trigger a notification.
    """

    def __init__(self, inner, store: Optional[CheckpointStore] = None) -> None:
        self._inner = inner
        self._store = store or CheckpointStore()

    @property
    def store(self) -> CheckpointStore:
        return self._store

    @property
    def inner(self):
        return self._inner

    def dispatch(self, result: JobResult) -> None:
        """Forward *result* to the inner dispatcher only on state transition."""
        if self._store.status_changed(result):
            self._inner.dispatch(result)
        self._store.record(result)
