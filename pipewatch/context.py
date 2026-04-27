"""Context manager interface for monitoring pipeline jobs."""

import logging
from typing import Optional

from pipewatch.config import PipewatchConfig
from pipewatch.monitor import PipelineMonitor, JobResult

logger = logging.getLogger(__name__)


class watch:
    """Context manager that monitors a pipeline job block.

    Usage::

        with watch("my-etl-job") as job:
            run_pipeline()

        print(job.result.duration_seconds)
    """

    def __init__(self, job_name: str, config: Optional[PipewatchConfig] = None):
        self.job_name = job_name
        self.config = config
        self._monitor: Optional[PipelineMonitor] = None
        self.result: Optional[JobResult] = None

    def __enter__(self) -> "watch":
        self._monitor = PipelineMonitor(job_name=self.job_name, config=self.config)
        self._monitor.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        assert self._monitor is not None

        if exc_type is not None:
            error_msg = f"{exc_type.__name__}: {exc_val}"
            logger.error("Job '%s' raised an exception: %s", self.job_name, error_msg)
            self.result = self._monitor.finish(success=False, error_message=error_msg)
        else:
            self.result = self._monitor.finish(success=True)

        # Do not suppress the exception
        return False
