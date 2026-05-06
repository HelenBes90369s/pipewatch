"""Tag-based filtering for alert dispatchers."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Iterable

from pipewatch.monitor import JobResult


@dataclass
class TagFilter:
    """Matches a JobResult based on its tags."""

    required: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    def matches(self, result: JobResult) -> bool:
        """Return True when *result* satisfies all tag constraints."""
        tags: list[str] = getattr(result, "tags", []) or []
        for pattern in self.required:
            if not any(fnmatch(t, pattern) for t in tags):
                return False
        for pattern in self.excluded:
            if any(fnmatch(t, pattern) for t in tags):
                return False
        return True


class TagRegistry:
    """Maintains a set of known tags and validates incoming results."""

    def __init__(self) -> None:
        self._known: set[str] = set()

    def register(self, *tags: str) -> None:
        """Register one or more tag names as known."""
        self._known.update(tags)

    @property
    def known_tags(self) -> frozenset[str]:
        return frozenset(self._known)

    def unknown_tags(self, result: JobResult) -> list[str]:
        """Return tags on *result* that have not been registered."""
        tags: Iterable[str] = getattr(result, "tags", []) or []
        return [t for t in tags if t not in self._known]
