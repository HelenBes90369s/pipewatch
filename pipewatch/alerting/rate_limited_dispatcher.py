"""Alert dispatcher that enforces per-job rate limits before forwarding."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pipewatch.alerting.rate_limit import AlertRateLimiter, RateLimitConfig
from pipewatch.monitor import JobResult


class _Dispatcher(Protocol):
    def dispatch(self, result: JobResult) -> None:
        ...


class RateLimitedAlertDispatcher:
    """Wraps an inner dispatcher and drops alerts that exceed the rate limit."""

    def __init__(
        self,
        inner: _Dispatcher,
        config: RateLimitConfig | None = None,
        limiter: AlertRateLimiter | None = None,
    ) -> None:
        self._inner = inner
        self._limiter = limiter or AlertRateLimiter(config)

    @property
    def limiter(self) -> AlertRateLimiter:
        return self._limiter

    def dispatch(self, result: JobResult, now: datetime | None = None) -> None:
        """Forward *result* to the inner dispatcher only if within rate limit."""
        job_name = result.job_name
        now = now or datetime.utcnow()
        if not self._limiter.is_allowed(job_name, now):
            return
        self._limiter.record(job_name, now)
        self._inner.dispatch(result)
