"""Alert suppression windows — silence alerts during scheduled maintenance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class SuppressionWindow:
    """A time window during which alerts are suppressed."""

    start: time
    end: time
    days: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon, 6=Sun
    label: str = ""

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if the suppression window is active at *at* (default: now)."""
        now = at or datetime.now()
        if now.weekday() not in self.days:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # Overnight window e.g. 22:00 – 06:00
        return current >= self.start or current <= self.end


class SuppressionSchedule:
    """Collection of suppression windows; suppresses when ANY window is active."""

    def __init__(self, windows: Optional[List[SuppressionWindow]] = None) -> None:
        self.windows: List[SuppressionWindow] = windows or []

    def add(self, window: SuppressionWindow) -> None:
        self.windows.append(window)

    def is_suppressed(self, at: Optional[datetime] = None) -> bool:
        return any(w.is_active(at) for w in self.windows)

    @classmethod
    def from_config(cls, entries: List[dict]) -> "SuppressionSchedule":
        """Build a schedule from a list of config dicts.

        Each dict may contain:
          start: "HH:MM"
          end:   "HH:MM"
          days:  [0, 1, 2, 3, 4]  (optional)
          label: "maintenance"    (optional)
        """
        windows = []
        for entry in entries:
            start = _parse_time(entry["start"])
            end = _parse_time(entry["end"])
            days = entry.get("days", list(range(7)))
            label = entry.get("label", "")
            windows.append(SuppressionWindow(start=start, end=end, days=days, label=label))
        return cls(windows)


def _parse_time(value: str) -> time:
    """Parse 'HH:MM' into a :class:`datetime.time`."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not match:
        raise ValueError(f"Invalid time format: {value!r}. Expected HH:MM.")
    return time(int(match.group(1)), int(match.group(2)))
