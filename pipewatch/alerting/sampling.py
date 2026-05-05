"""Alert sampling — reduce noise by only dispatching a fraction of alerts."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from pipewatch.monitor import JobResult


@dataclass
class SamplingConfig:
    """Configuration for probabilistic alert sampling."""

    # Fraction of alerts to pass through (0.0 = none, 1.0 = all).
    rate: float = 1.0
    # Always send alerts for failures regardless of sample rate.
    always_send_failures: bool = True
    # Seed for reproducible sampling in tests; None means truly random.
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {self.rate}")


class AlertSampler:
    """Decides whether an alert should be forwarded based on a sampling rate."""

    def __init__(self, config: Optional[SamplingConfig] = None) -> None:
        self._config = config or SamplingConfig()
        self._rng = random.Random(self._config.seed)

    @property
    def config(self) -> SamplingConfig:
        return self._config

    def should_send(self, result: JobResult) -> bool:
        """Return True if this alert should be forwarded."""
        if self._config.always_send_failures and not result.success:
            return True
        return self._rng.random() < self._config.rate


class SampledAlertDispatcher:
    """Wraps an inner dispatcher and applies probabilistic sampling."""

    def __init__(self, inner, sampler: Optional[AlertSampler] = None) -> None:
        self._inner = inner
        self._sampler = sampler or AlertSampler()

    @property
    def sampler(self) -> AlertSampler:
        return self._sampler

    def dispatch(self, result: JobResult, history=None) -> None:
        """Forward *result* to the inner dispatcher only if sampling allows it."""
        if self._sampler.should_send(result):
            self._inner.dispatch(result, history)
