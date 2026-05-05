"""Dispatcher that uses AlertRouter to pick per-job notifiers."""
from __future__ import annotations

from typing import Dict, List

from pipewatch.alerting.dispatcher import AlertDispatcher
from pipewatch.alerting.routing import AlertRouter
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


class RoutedAlertDispatcher:
    """Wraps an AlertRouter and a registry of named notifiers.

    For each incoming result the router resolves which notifiers to use;
    an :class:`AlertDispatcher` is then constructed on-the-fly for that
    subset and asked to dispatch the alert.
    """

    def __init__(
        self,
        router: AlertRouter,
        notifiers: Dict[str, BaseNotifier],
    ) -> None:
        self._router = router
        self._notifiers = notifiers

    def dispatch(self, result: JobResult) -> None:
        names = self._router.resolve(result)
        selected: List[BaseNotifier] = [
            self._notifiers[n] for n in names if n in self._notifiers
        ]
        if not selected:
            return
        inner = AlertDispatcher(notifiers=selected)
        inner.dispatch(result)

    @property
    def router(self) -> AlertRouter:
        return self._router

    @property
    def notifiers(self) -> Dict[str, BaseNotifier]:
        return dict(self._notifiers)
