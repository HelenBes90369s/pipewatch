"""Rate limiting for alert dispatchers — caps alerts per job per time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List


@dataclass
class RateLimitConfig:
    max_alerts: int = 5
    window_seconds: int = 3600

    def __post_init__(self) -> None:
        if self.max_alerts < 1:
            raise ValueError("max_alerts must be at least 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")


class AlertRateLimiter:
    """Tracks per-job alert counts within a rolling time window."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._timestamps: Dict[str, List[datetime]] = defaultdict(list)

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def _prune(self, job_name: str, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        self._timestamps[job_name] = [
            ts for ts in self._timestamps[job_name] if ts > cutoff
        ]

    def is_allowed(self, job_name: str, now: datetime | None = None) -> bool:
        """Return True if an alert for *job_name* is within the rate limit."""
        now = now or datetime.utcnow()
        self._prune(job_name, now)
        return len(self._timestamps[job_name]) < self._config.max_alerts

    def record(self, job_name: str, now: datetime | None = None) -> None:
        """Record that an alert was sent for *job_name*."""
        now = now or datetime.utcnow()
        self._timestamps[job_name].append(now)

    def remaining(self, job_name: str, now: datetime | None = None) -> int:
        """Return how many more alerts are allowed in the current window."""
        now = now or datetime.utcnow()
        self._prune(job_name, now)
        used = len(self._timestamps[job_name])
        return max(0, self._config.max_alerts - used)
