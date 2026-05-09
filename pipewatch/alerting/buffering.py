"""Alert buffering: collect alerts up to a max size or time window, then flush."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Protocol

from pipewatch.monitor import JobResult


class _Dispatcher(Protocol):
    def dispatch(self, result: JobResult) -> None: ...


@dataclass
class BufferConfig:
    max_size: int = 10
    max_age_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_size < 1:
            raise ValueError("max_size must be at least 1")
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")


class AlertBuffer:
    """Buffers JobResult objects and flushes them to a dispatcher in bulk."""

    def __init__(self, config: BufferConfig | None = None) -> None:
        self._config = config or BufferConfig()
        self._buffer: List[JobResult] = []
        self._created_at: float = time.monotonic()

    @property
    def config(self) -> BufferConfig:
        return self._config

    def add(self, result: JobResult) -> None:
        self._buffer.append(result)

    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def size(self) -> int:
        return len(self._buffer)

    def age_seconds(self) -> float:
        return time.monotonic() - self._created_at

    def should_flush(self) -> bool:
        if self.is_empty():
            return False
        if self.size() >= self._config.max_size:
            return True
        if self.age_seconds() >= self._config.max_age_seconds:
            return True
        return False

    def flush(self, dispatcher: _Dispatcher) -> List[JobResult]:
        """Dispatch all buffered results and reset the buffer."""
        flushed = list(self._buffer)
        for result in flushed:
            dispatcher.dispatch(result)
        self._buffer.clear()
        self._created_at = time.monotonic()
        return flushed


class BufferedAlertDispatcher:
    """Wraps a dispatcher, buffering alerts and flushing when the buffer is ready."""

    def __init__(
        self,
        inner: _Dispatcher,
        config: BufferConfig | None = None,
    ) -> None:
        self._inner = inner
        self._buffer = AlertBuffer(config)

    @property
    def buffer(self) -> AlertBuffer:
        return self._buffer

    @property
    def inner(self) -> _Dispatcher:
        return self._inner

    def dispatch(self, result: JobResult) -> None:
        self._buffer.add(result)
        if self._buffer.should_flush():
            self._buffer.flush(self._inner)

    def flush(self) -> List[JobResult]:
        """Force-flush the buffer regardless of thresholds."""
        return self._buffer.flush(self._inner)
