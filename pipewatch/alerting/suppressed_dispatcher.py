"""Alert dispatcher that honours a suppression schedule."""

from __future__ import annotations

from typing import List, Optional

from pipewatch.alerting.dispatcher import AlertDispatcher
from pipewatch.alerting.suppression import SuppressionSchedule
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


class SuppressedAlertDispatcher:
    """Wraps :class:`AlertDispatcher` and skips dispatch during suppression windows."""

    def __init__(
        self,
        notifiers: List[BaseNotifier],
        schedule: SuppressionSchedule,
        inner: Optional[AlertDispatcher] = None,
    ) -> None:
        self._schedule = schedule
        self._inner = inner or AlertDispatcher(notifiers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch(self, result: JobResult) -> bool:
        """Dispatch alerts unless the current time falls inside a suppression window.

        Returns True if at least one notification was sent, False otherwise.
        """
        if self._schedule.is_suppressed():
            return False
        return self._inner.dispatch(result)

    @property
    def schedule(self) -> SuppressionSchedule:
        return self._schedule
