"""Core pipeline monitor that tracks job execution and triggers alerts."""

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List

from pipewatch.config import PipewatchConfig, load_config
from pipewatch.notifiers.slack import SlackNotifier
from pipewatch.notifiers.email import EmailNotifier

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    name: str
    success: bool
    duration_seconds: float
    started_at: datetime
    finished_at: datetime
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class PipelineMonitor:
    """Monitors a pipeline job and sends alerts on failure or timeout."""

    def __init__(self, job_name: str, config: Optional[PipewatchConfig] = None):
        self.job_name = job_name
        self.config = config or load_config()
        self._start_time: Optional[float] = None
        self._notifiers = self._build_notifiers()

    def _build_notifiers(self) -> List:
        notifiers = []
        if self.config.slack and self.config.slack.webhook_url:
            notifiers.append(SlackNotifier(self.config.slack))
        if self.config.email and self.config.email.smtp_host:
            notifiers.append(EmailNotifier(self.config.email))
        return notifiers

    def start(self) -> None:
        """Record the start time of the job."""
        self._start_time = time.monotonic()
        logger.info("Job '%s' started.", self.job_name)

    def finish(self, success: bool = True, error_message: Optional[str] = None) -> JobResult:
        """Record job completion and trigger alerts if needed."""
        if self._start_time is None:
            raise RuntimeError("monitor.start() must be called before finish().")

        duration = time.monotonic() - self._start_time
        now = datetime.utcnow()
        result = JobResult(
            name=self.job_name,
            success=success,
            duration_seconds=round(duration, 3),
            started_at=now - timedelta(seconds=duration),
            finished_at=now,
            error_message=error_message,
        )

        if not success:
            self._alert(result)
        else:
            logger.info("Job '%s' completed successfully in %.2fs.", self.job_name, duration)

        return result

    def _alert(self, result: JobResult) -> None:
        message = (
            f":rotating_light: Job *{result.name}* failed after "
            f"{result.duration_seconds:.2f}s."
        )
        if result.error_message:
            message += f"\nError: {result.error_message}"

        for notifier in self._notifiers:
            try:
                notifier.send(subject=f"[pipewatch] Job '{result.name}' failed", body=message)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Notifier %s failed: %s", type(notifier).__name__, exc)
