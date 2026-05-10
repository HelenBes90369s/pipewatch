"""Alert payload redaction — strips sensitive fields before notifications are sent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pipewatch.monitor import JobResult

_DEFAULT_PATTERNS: list[str] = [
    r"password",
    r"secret",
    r"token",
    r"api[_-]?key",
    r"credential",
    r"auth",
]

_REDACTED = "[REDACTED]"


@dataclass
class RedactionConfig:
    """Configuration for the field redactor."""

    patterns: list[str] = field(default_factory=lambda: list(_DEFAULT_PATTERNS))
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled = [re.compile(p, flags) for p in self.patterns]

    def is_sensitive(self, key: str) -> bool:
        """Return True if *key* matches any redaction pattern."""
        return any(rx.search(key) for rx in self._compiled)


class AlertRedactor:
    """Recursively redacts sensitive keys from a mapping derived from a JobResult."""

    def __init__(self, config: RedactionConfig | None = None) -> None:
        self._config = config or RedactionConfig()

    @property
    def config(self) -> RedactionConfig:
        return self._config

    def redact(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a new dict with sensitive values replaced by *[REDACTED]*."""
        return {k: self._redact_value(k, v) for k, v in data.items()}

    def _redact_value(self, key: str, value: Any) -> Any:
        if self._config.is_sensitive(key):
            return _REDACTED
        if isinstance(value, dict):
            return {k: self._redact_value(k, v) for k, v in value.items()}
        return value

    def redact_result(self, result: JobResult) -> dict[str, Any]:
        """Convenience: convert *result* to a dict then redact it."""
        raw: dict[str, Any] = {
            "job_name": result.job_name,
            "success": result.success,
            "error": result.error,
            "metadata": dict(result.metadata) if result.metadata else {},
        }
        return self.redact(raw)
