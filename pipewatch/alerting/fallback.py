"""Fallback dispatcher: tries a primary notifier and falls back to alternates on failure."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from pipewatch.monitor import JobResult


class _Dispatcher(Protocol):
    def dispatch(self, result: JobResult) -> None:
        ...


@dataclass
class FallbackAlertDispatcher:
    """Dispatch to the first notifier that succeeds; try alternates on failure.

    Each dispatcher's ``dispatch`` method is expected to raise an exception if
    the underlying send fails.  The first dispatcher that does *not* raise is
    considered successful and no further dispatchers are tried.
    """

    _primary: _Dispatcher
    _fallbacks: List[_Dispatcher] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    @property
    def primary(self) -> _Dispatcher:
        return self._primary

    @property
    def fallbacks(self) -> List[_Dispatcher]:
        return list(self._fallbacks)

    def dispatch(self, result: JobResult) -> None:
        """Try primary then each fallback in order until one succeeds."""
        candidates = [self._primary] + self._fallbacks
        last_exc: Exception | None = None

        for dispatcher in candidates:
            try:
                dispatcher.dispatch(result)
                return  # success – stop trying
            except Exception as exc:  # noqa: BLE001
                last_exc = exc

        # All dispatchers failed – re-raise the last exception so callers
        # are aware that nothing got through.
        if last_exc is not None:
            raise last_exc
