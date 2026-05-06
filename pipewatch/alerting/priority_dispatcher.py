"""Dispatcher that routes alerts to notifiers based on priority level."""
from __future__ import annotations

from typing import Dict, List, Optional

from pipewatch.monitor import JobResult
from pipewatch.alerting.priority import Priority, PriorityClassifier


class PriorityAlertDispatcher:
    """Dispatches alerts only to notifiers registered for the result's priority.

    Notifiers registered for a given priority also receive alerts for any
    *higher* priority unless ``exact_match`` is True.
    """

    def __init__(
        self,
        classifier: PriorityClassifier,
        exact_match: bool = False,
    ) -> None:
        self._classifier = classifier
        self._exact_match = exact_match
        self._notifiers: Dict[Priority, List] = {p: [] for p in Priority}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, notifier, priority: Priority) -> None:
        """Register *notifier* to receive alerts at *priority* (and above)."""
        self._notifiers[priority].append(notifier)

    def dispatch(self, result: JobResult) -> None:
        """Classify *result* and forward to appropriate notifiers."""
        priority = self._classifier.classify(result)
        for notifier in self._notifiers_for(priority):
            notifier.send(result)

    @property
    def classifier(self) -> PriorityClassifier:
        return self._classifier

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notifiers_for(self, priority: Priority) -> List:
        if self._exact_match:
            return list(self._notifiers[priority])
        collected = []
        for p, notifiers in self._notifiers.items():
            if priority >= p:
                collected.extend(notifiers)
        return collected
