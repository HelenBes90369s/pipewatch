"""A dispatcher wrapper that redacts sensitive data before forwarding alerts."""

from __future__ import annotations

from typing import Protocol

from pipewatch.alerting.redaction import AlertRedactor, RedactionConfig
from pipewatch.monitor import JobResult


class _Dispatcher(Protocol):
    def dispatch(self, result: JobResult) -> None:
        ...


class RedactedAlertDispatcher:
    """Wraps an inner dispatcher and redacts the result metadata before dispatch.

    The inner dispatcher still receives the original *JobResult* object;
    redaction is applied to produce a sanitised audit/log representation.
    Notifiers that build their own payloads from the result are therefore
    unaffected — pair this with :class:`AlertAnnotator` to inject the
    sanitised snapshot into the result metadata when full redaction of
    outbound payloads is required.
    """

    def __init__(
        self,
        inner: _Dispatcher,
        redactor: AlertRedactor | None = None,
    ) -> None:
        self._inner = inner
        self._redactor = redactor or AlertRedactor()

    @property
    def inner(self) -> _Dispatcher:
        return self._inner

    @property
    def redactor(self) -> AlertRedactor:
        return self._redactor

    def dispatch(self, result: JobResult) -> None:
        """Redact *result* metadata then forward to the inner dispatcher."""
        if result.metadata:
            sanitised = self._redactor.redact(dict(result.metadata))
            # Replace metadata with the sanitised copy for downstream dispatch.
            redacted_result = JobResult(
                job_name=result.job_name,
                success=result.success,
                error=result.error,
                metrics=result.metrics,
                metadata=sanitised,
            )
        else:
            redacted_result = result
        self._inner.dispatch(redacted_result)
