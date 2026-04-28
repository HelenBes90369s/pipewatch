"""Job run history tracking — stores and queries past JobResult records."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pipewatch.monitor import JobResult


@dataclass
class HistoryEntry:
    job_name: str
    success: bool
    started_at: Optional[str]
    elapsed_seconds: Optional[float]
    error_message: Optional[str]

    @classmethod
    def from_result(cls, result: JobResult) -> "HistoryEntry":
        started = (
            result.metrics.started_at.isoformat()
            if result.metrics and result.metrics.started_at
            else None
        )
        elapsed = (
            result.metrics.elapsed_seconds()
            if result.metrics
            else None
        )
        return cls(
            job_name=result.job_name,
            success=result.success,
            started_at=started,
            elapsed_seconds=elapsed,
            error_message=result.error_message,
        )

    def to_dict(self) -> dict:
        return asdict(self)


class JobHistory:
    """Persist and retrieve job run history from a newline-delimited JSON file."""

    def __init__(self, path: str | os.PathLike = ".pipewatch_history.jsonl") -> None:
        self._path = Path(path)

    def record(self, result: JobResult) -> None:
        entry = HistoryEntry.from_result(result)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def load(self, job_name: Optional[str] = None) -> List[HistoryEntry]:
        if not self._path.exists():
            return []
        entries: List[HistoryEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = HistoryEntry(**data)
                if job_name is None or entry.job_name == job_name:
                    entries.append(entry)
        return entries

    def last(self, job_name: str) -> Optional[HistoryEntry]:
        entries = self.load(job_name=job_name)
        return entries[-1] if entries else None

    def failure_streak(self, job_name: str) -> int:
        """Return the number of consecutive failures at the tail of history."""
        entries = self.load(job_name=job_name)
        streak = 0
        for entry in reversed(entries):
            if not entry.success:
                streak += 1
            else:
                break
        return streak
