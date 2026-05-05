"""Alert aggregation: batch multiple job results into a single notification."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pipewatch.monitor import JobResult


@dataclass
class AggregationConfig:
    max_size: int = 10
    max_age_seconds: float = 300.0
    only_failures: bool = False


@dataclass
class AggregatedBatch:
    results: List[JobResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add(self, result: JobResult) -> None:
        self.results.append(result)

    def is_empty(self) -> bool:
        return len(self.results) == 0

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        now = now or datetime.utcnow()
        return (now - self.created_at).total_seconds()

    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    def summary(self) -> str:
        total = len(self.results)
        failures = self.failure_count()
        successes = self.success_count()
        return (
            f"Aggregated {total} job(s): "
            f"{successes} succeeded, {failures} failed."
        )


class AlertAggregator:
    """Collects JobResults and flushes them as a batch when thresholds are met."""

    def __init__(self, config: Optional[AggregationConfig] = None) -> None:
        self._config = config or AggregationConfig()
        self._batch = AggregatedBatch()

    @property
    def config(self) -> AggregationConfig:
        return self._config

    def add(self, result: JobResult) -> Optional[AggregatedBatch]:
        """Add a result. Returns a flushed batch if a threshold is reached."""
        if self._config.only_failures and result.success:
            return None

        self._batch.add(result)

        if self._should_flush():
            return self.flush()
        return None

    def flush(self) -> Optional[AggregatedBatch]:
        """Force-flush the current batch regardless of thresholds."""
        if self._batch.is_empty():
            return None
        batch = self._batch
        self._batch = AggregatedBatch()
        return batch

    def _should_flush(self, now: Optional[datetime] = None) -> bool:
        if len(self._batch.results) >= self._config.max_size:
            return True
        if self._batch.age_seconds(now) >= self._config.max_age_seconds:
            return True
        return False

    def pending_count(self) -> int:
        return len(self._batch.results)
