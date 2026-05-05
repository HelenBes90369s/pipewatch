"""Alert deduplication: suppress repeated identical alerts within a window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewatch.monitor import JobResult


@dataclass
class DeduplicationConfig:
    """Configuration for alert deduplication."""

    window_seconds: int = 300  # 5 minutes default
    include_error_message: bool = False


@dataclass
class _CacheEntry:
    fingerprint: str
    first_seen: float
    count: int = 1


class AlertDeduplicator:
    """Tracks recently sent alerts and suppresses duplicates within a time window."""

    def __init__(self, config: Optional[DeduplicationConfig] = None) -> None:
        self._config = config or DeduplicationConfig()
        self._cache: Dict[str, _CacheEntry] = {}

    def _fingerprint(self, result: JobResult) -> str:
        """Produce a stable fingerprint for a job result."""
        parts = [result.job_name, str(result.success)]
        if self._config.include_error_message and result.error_message:
            parts.append(result.error_message)
        raw = "|".join(parts)
        return hashlib.sha1(raw.encode()).hexdigest()

    def _evict_expired(self, now: float) -> None:
        expired = [
            key
            for key, entry in self._cache.items()
            if (now - entry.first_seen) >= self._config.window_seconds
        ]
        for key in expired:
            del self._cache[key]

    def is_duplicate(self, result: JobResult) -> bool:
        """Return True if an identical alert was already sent within the window."""
        now = time.monotonic()
        self._evict_expired(now)
        fp = self._fingerprint(result)
        return fp in self._cache

    def record(self, result: JobResult) -> None:
        """Record that an alert for *result* has been sent."""
        now = time.monotonic()
        self._evict_expired(now)
        fp = self._fingerprint(result)
        if fp in self._cache:
            self._cache[fp].count += 1
        else:
            self._cache[fp] = _CacheEntry(fingerprint=fp, first_seen=now)

    def pending_count(self, result: JobResult) -> int:
        """Return how many times this alert has fired within the current window."""
        fp = self._fingerprint(result)
        entry = self._cache.get(fp)
        return entry.count if entry else 0
