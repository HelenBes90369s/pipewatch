"""Alert enrichment: attach contextual metadata to JobResult before dispatching."""
from __future__ import annotations

import platform
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pipewatch.monitor import JobResult


@dataclass
class EnrichmentContext:
    """Extra metadata to attach to an alert payload."""

    hostname: str = field(default_factory=platform.node)
    pid: int = field(default_factory=os.getpid)
    environment: str = field(default_factory=lambda: os.environ.get("PIPEWATCH_ENV", "production"))
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "hostname": self.hostname,
            "pid": self.pid,
            "environment": self.environment,
        }
        data.update(self.extra)
        return data


class AlertEnricher:
    """Wraps an inner dispatcher and injects enrichment metadata into each result."""

    def __init__(self, inner, context: Optional[EnrichmentContext] = None) -> None:
        self._inner = inner
        self._context = context or EnrichmentContext()

    @property
    def context(self) -> EnrichmentContext:
        return self._context

    def dispatch(self, result: JobResult) -> None:
        enriched = self._enrich(result)
        self._inner.dispatch(enriched)

    def _enrich(self, result: JobResult) -> JobResult:
        """Return a shallow copy of *result* with enrichment metadata merged in."""
        extra = dict(result.metadata) if hasattr(result, "metadata") and result.metadata else {}
        extra.update(self._context.to_dict())
        # JobResult is a dataclass — replace metadata field non-destructively.
        return JobResult(
            job_name=result.job_name,
            success=result.success,
            error=result.error,
            metrics=result.metrics,
            metadata=extra,
        )
