"""Alert digest: batch multiple job results into a single notification."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pipewatch.monitor import JobResult


@dataclass
class DigestEntry:
    job_name: str
    success: bool
    elapsed_human: str
    error_message: Optional[str] = None

    @classmethod
    def from_result(cls, result: JobResult) -> "DigestEntry":
        return cls(
            job_name=result.job_name,
            success=result.success,
            elapsed_human=result.metrics.elapsed_human() if result.metrics else "n/a",
            error_message=result.error_message,
        )

    def summary_line(self) -> str:
        status = "✅" if self.success else "❌"
        line = f"{status} *{self.job_name}* — {self.elapsed_human}"
        if self.error_message:
            line += f"\n   _Error: {self.error_message}_"
        return line


@dataclass
class AlertDigest:
    entries: List[DigestEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add(self, result: JobResult) -> None:
        self.entries.append(DigestEntry.from_result(result))

    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def failure_count(self) -> int:
        return sum(1 for e in self.entries if not e.success)

    def success_count(self) -> int:
        return sum(1 for e in self.entries if e.success)

    def render_text(self) -> str:
        if self.is_empty():
            return "No jobs recorded in this digest period."

        lines = [
            f"*Pipeline Digest* — {self.created_at.strftime('%Y-%m-%d %H:%M')} UTC",
            f"Total: {len(self.entries)} | "
            f"✅ {self.success_count()} | ❌ {self.failure_count()}",
            "",
        ]
        for entry in self.entries:
            lines.append(entry.summary_line())
        return "\n".join(lines)

    def flush(self, notifiers: list) -> None:
        """Send the digest via all provided notifiers and clear entries."""
        if self.is_empty():
            return
        message = self.render_text()
        for notifier in notifiers:
            notifier.send(message)
        self.entries.clear()
        self.created_at = datetime.utcnow()
