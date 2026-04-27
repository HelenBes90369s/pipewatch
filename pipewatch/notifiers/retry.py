"""Retry wrapper for notifiers with exponential backoff."""

import time
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0


class RetryConfig:
    """Configuration for retry behaviour."""

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        base_delay: float = DEFAULT_BASE_DELAY,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor

    def delay_for(self, attempt: int) -> float:
        """Return the delay in seconds before the given attempt (0-indexed)."""
        if attempt == 0:
            return 0.0
        return self.base_delay * (self.backoff_factor ** (attempt - 1))


class RetryingNotifier:
    """Wraps any notifier and retries failed sends with exponential backoff."""

    def __init__(self, notifier: Any, retry_config: RetryConfig | None = None) -> None:
        self._notifier = notifier
        self._retry = retry_config or RetryConfig()

    @property
    def name(self) -> str:
        return getattr(self._notifier, "name", type(self._notifier).__name__)

    def send(self, job_result: Any) -> bool:
        """Attempt to send, retrying on failure up to max_attempts times."""
        last_success = False
        for attempt in range(self._retry.max_attempts):
            delay = self._retry.delay_for(attempt)
            if delay > 0:
                logger.debug(
                    "[%s] Retry attempt %d/%d after %.1fs delay",
                    self.name,
                    attempt + 1,
                    self._retry.max_attempts,
                    delay,
                )
                time.sleep(delay)
            try:
                last_success = self._notifier.send(job_result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] Attempt %d raised: %s", self.name, attempt + 1, exc)
                last_success = False

            if last_success:
                if attempt > 0:
                    logger.info("[%s] Succeeded on attempt %d", self.name, attempt + 1)
                return True

        logger.error("[%s] All %d attempts failed.", self.name, self._retry.max_attempts)
        return False


def with_retry(notifier: Any, retry_config: RetryConfig | None = None) -> RetryingNotifier:
    """Convenience factory: wrap *notifier* in a RetryingNotifier."""
    return RetryingNotifier(notifier, retry_config)
