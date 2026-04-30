"""Alert throttling to prevent notification floods."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    """Configuration for alert throttling."""

    min_interval_seconds: int = 300  # 5 minutes default
    max_alerts_per_hour: int = 10


class AlertThrottle:
    """Tracks alert history to suppress duplicate/excessive notifications."""

    def __init__(self, config: Optional[ThrottleConfig] = None) -> None:
        self._config = config or ThrottleConfig()
        self._last_alert: Dict[str, datetime] = {}
        self._alert_counts: Dict[str, list] = {}

    def should_send(self, job_name: str) -> bool:
        """Return True if an alert should be sent for the given job."""
        now = datetime.utcnow()

        if not self._interval_ok(job_name, now):
            return False

        if not self._rate_ok(job_name, now):
            return False

        return True

    def record(self, job_name: str) -> None:
        """Record that an alert was sent for the given job."""
        now = datetime.utcnow()
        self._last_alert[job_name] = now
        self._alert_counts.setdefault(job_name, []).append(now)

    def reset(self, job_name: str) -> None:
        """Clear throttle history for the given job.

        Useful when a job recovers and future alerts should not be suppressed
        due to prior failures.
        """
        self._last_alert.pop(job_name, None)
        self._alert_counts.pop(job_name, None)

    def _interval_ok(self, job_name: str, now: datetime) -> bool:
        last = self._last_alert.get(job_name)
        if last is None:
            return True
        elapsed = (now - last).total_seconds()
        return elapsed >= self._config.min_interval_seconds

    def _rate_ok(self, job_name: str, now: datetime) -> bool:
        cutoff = now - timedelta(hours=1)
        recent = [
            ts for ts in self._alert_counts.get(job_name, [])
            if ts > cutoff
        ]
        self._alert_counts[job_name] = recent
        return len(recent) < self._config.max_alerts_per_hour
