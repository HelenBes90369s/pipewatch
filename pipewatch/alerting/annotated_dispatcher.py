"""Dispatcher that annotates results and forwards them to an inner dispatcher."""
from __future__ import annotations

from typing import Any, Dict

from pipewatch.alerting.annotation import AlertAnnotator
from pipewatch.monitor import JobResult


class _Dispatcher:
    """Minimal protocol expected of the inner dispatcher."""

    def dispatch(self, result: JobResult) -> None:  # pragma: no cover
        raise NotImplementedError


class AnnotatedAlertDispatcher:
    """Wraps an inner dispatcher; exposes annotation metadata via *last_annotation*.

    The annotation dict is stored after each ``dispatch`` call so that callers
    (e.g. notifiers, tests) can inspect what metadata was produced.
    """

    def __init__(self, inner: _Dispatcher, annotator: AlertAnnotator) -> None:
        self._inner = inner
        self._annotator = annotator
        self._last_annotation: Dict[str, Any] = {}

    @property
    def annotator(self) -> AlertAnnotator:
        return self._annotator

    @property
    def inner(self) -> _Dispatcher:
        return self._inner

    @property
    def last_annotation(self) -> Dict[str, Any]:
        """Annotation dict produced during the most recent ``dispatch`` call."""
        return dict(self._last_annotation)

    def dispatch(self, result: JobResult) -> None:
        self._last_annotation = self._annotator.annotate(result)
        self._inner.dispatch(result)
