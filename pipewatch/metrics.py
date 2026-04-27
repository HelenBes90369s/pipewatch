"""Runtime metrics collection for monitored pipeline jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobMetrics:
    """Holds timing and resource metrics for a single pipeline job run."""

    job_name: str
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    records_processed: Optional[int] = None
    extra: dict = field(default_factory=dict)

    def stop(self) -> None:
        """Record the end time of the job."""
        self.end_time = time.monotonic()

    @property
    def elapsed_seconds(self) -> Optional[float]:
        """Return elapsed wall-clock time in seconds, or None if not finished."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def elapsed_human(self) -> str:
        """Return a human-readable elapsed time string."""
        seconds = self.elapsed_seconds
        if seconds is None:
            return "in progress"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes, secs = divmod(int(seconds), 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m {secs}s"

    def to_dict(self) -> dict:
        """Serialize metrics to a plain dictionary for use in notifications."""
        return {
            "job_name": self.job_name,
            "elapsed_seconds": self.elapsed_seconds,
            "elapsed_human": self.elapsed_human,
            "peak_memory_mb": self.peak_memory_mb,
            "records_processed": self.records_processed,
            **self.extra,
        }


def collect_memory_mb() -> float:
    """Return current process RSS memory usage in megabytes."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux ru_maxrss is in kilobytes; on macOS it is in bytes.
        import sys
        if sys.platform == "darwin":
            return usage / (1024 * 1024)
        return usage / 1024
    except Exception:
        return 0.0
