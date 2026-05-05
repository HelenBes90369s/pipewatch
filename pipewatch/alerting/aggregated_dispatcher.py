"""Dispatcher that aggregates results and sends batched notifications."""
from __future__ import annotations

from typing import List, Optional

from pipewatch.alerting.aggregation import AggregatedBatch, AggregationConfig, AlertAggregator
from pipewatch.monitor import JobResult
from pipewatch.notifiers import BaseNotifier


class AggregatedAlertDispatcher:
    """Wraps an inner notifier and sends alerts in aggregated batches.

    Call ``dispatch`` for each job result.  An alert is sent only when the
    aggregator decides the batch is ready to flush (size or age threshold).
    Call ``flush`` at shutdown to drain any remaining results.
    """

    def __init__(
        self,
        notifiers: List[BaseNotifier],
        config: Optional[AggregationConfig] = None,
    ) -> None:
        self._notifiers = notifiers
        self._aggregator = AlertAggregator(config)

    @property
    def aggregator(self) -> AlertAggregator:
        return self._aggregator

    @property
    def notifiers(self) -> List[BaseNotifier]:
        return self._notifiers

    def dispatch(self, result: JobResult) -> bool:
        """Add *result* to the current batch.  Returns True if a batch was sent."""
        batch = self._aggregator.add(result)
        if batch is not None:
            return self._send_batch(batch)
        return False

    def flush(self) -> bool:
        """Flush any pending results immediately.  Returns True if anything was sent."""
        batch = self._aggregator.flush()
        if batch is not None:
            return self._send_batch(batch)
        return False

    def _send_batch(self, batch: AggregatedBatch) -> bool:
        message = self._format_batch(batch)
        sent_any = False
        for notifier in self._notifiers:
            if notifier.send(message):
                sent_any = True
        return sent_any

    @staticmethod
    def _format_batch(batch: AggregatedBatch) -> str:
        lines = [batch.summary()]
        for r in batch.results:
            status = "OK" if r.success else "FAIL"
            duration = f"{r.metrics.elapsed_seconds():.1f}s" if r.metrics else "n/a"
            error = f" — {r.error_message}" if r.error_message else ""
            lines.append(f"  [{status}] {r.job_name} ({duration}){error}")
        return "\n".join(lines)
