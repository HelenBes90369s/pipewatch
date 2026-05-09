"""Audit log for alert dispatch events."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pipewatch.monitor import JobResult

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    job_name: str
    success: bool
    alert_sent: bool
    notifier: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "success": self.success,
            "alert_sent": self.alert_sent,
            "notifier": self.notifier,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_result(
        cls,
        result: JobResult,
        *,
        alert_sent: bool,
        notifier: str,
        reason: str,
    ) -> "AuditEntry":
        return cls(
            job_name=result.job_name,
            success=result.success,
            alert_sent=alert_sent,
            notifier=notifier,
            reason=reason,
        )


class AlertAuditLog:
    """Appends structured audit entries to a newline-delimited JSON file."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def record(self, entry: AuditEntry) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as exc:
            logger.warning("audit log write failed: %s", exc)

    def read_all(self) -> List[AuditEntry]:
        if not self._path.exists():
            return []
        entries: List[AuditEntry] = []
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(
                        AuditEntry(
                            job_name=data["job_name"],
                            success=data["success"],
                            alert_sent=data["alert_sent"],
                            notifier=data["notifier"],
                            reason=data["reason"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                        )
                    )
                except (KeyError, ValueError) as exc:
                    logger.warning("skipping malformed audit entry: %s", exc)
        return entries
