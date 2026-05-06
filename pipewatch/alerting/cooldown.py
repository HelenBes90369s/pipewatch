"""Per-job cooldown enforcement: suppress repeated alerts within a quiet period."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CooldownConfig:
    """Configuration for alert cooldown behaviour."""

    # Minimum seconds that must pass between two alerts for the same job.
    period_seconds: int = 300  # 5 minutes

    def __post_init__(self) -> None:
        if self.period_seconds < 0:
            raise ValueError("period_seconds must be >= 0")


class AlertCooldown:
    """Tracks the last alert time per job and decides whether a new alert may fire."""

    def __init__(self, config: Optional[CooldownConfig] = None) -> None:
        self._config: CooldownConfig = config or CooldownConfig()
        self._last_alert: Dict[str, float] = {}

    @property
    def config(self) -> CooldownConfig:
        return self._config

    def should_send(self, job_name: str) -> bool:
        """Return True if enough time has elapsed since the last alert for *job_name*."""
        if self._config.period_seconds == 0:
            return True
        last = self._last_alert.get(job_name)
        if last is None:
            return True
        return (time.monotonic() - last) >= self._config.period_seconds

    def record(self, job_name: str) -> None:
        """Record that an alert was just sent for *job_name*."""
        self._last_alert[job_name] = time.monotonic()

    def reset(self, job_name: str) -> None:
        """Clear the cooldown state for *job_name* (e.g. after a successful run)."""
        self._last_alert.pop(job_name, None)

    def remaining_seconds(self, job_name: str) -> float:
        """Return how many seconds remain in the cooldown for *job_name* (0 if none)."""
        last = self._last_alert.get(job_name)
        if last is None:
            return 0.0
        elapsed = time.monotonic() - last
        remaining = self._config.period_seconds - elapsed
        return max(0.0, remaining)
