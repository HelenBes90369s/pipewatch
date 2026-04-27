"""Context manager for wrapping pipeline jobs with monitoring and metrics."""

from __future__ import annotations

from typing import Optional

from pipewatch.metrics import JobMetrics, collect_memory_mb
from pipewatch.monitor import PipelineMonitor


class watch:
    """Context manager that monitors a pipeline job and collects metrics.

    Usage::

        with watch("my_etl_job", monitor=monitor) as ctx:
            run_pipeline()
            ctx.metrics.records_processed = 42_000
    """

    def __init__(
        self,
        job_name: str,
        monitor: Optional[PipelineMonitor] = None,
        track_memory: bool = True,
    ) -> None:
        self.job_name = job_name
        self.monitor = monitor
        self.track_memory = track_memory
        self.metrics: JobMetrics = JobMetrics(job_name=job_name)
        self._exc_type = None

    def __enter__(self) -> "watch":
        self.metrics = JobMetrics(job_name=self.job_name)
        if self.monitor is not None:
            self.monitor.start(self.job_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.metrics.stop()

        if self.track_memory:
            self.metrics.peak_memory_mb = collect_memory_mb()

        if self.monitor is not None:
            if exc_type is None:
                self.monitor.finish(
                    success=True,
                    metadata=self.metrics.to_dict(),
                )
            else:
                self.monitor.finish(
                    success=False,
                    error=str(exc_val),
                    metadata=self.metrics.to_dict(),
                )

        # Do not suppress exceptions
        return False
