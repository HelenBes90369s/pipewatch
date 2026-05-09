"""Alert annotation support: attach structured metadata to alerts before dispatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pipewatch.monitor import JobResult


@dataclass
class AnnotationConfig:
    """Static key/value annotations to attach to every alert."""

    labels: Dict[str, str] = field(default_factory=dict)
    environment: str = "production"
    team: Optional[str] = None


class AlertAnnotator:
    """Attaches structured annotations to a JobResult before passing it on."""

    def __init__(self, config: AnnotationConfig) -> None:
        self._config = config

    @property
    def config(self) -> AnnotationConfig:
        return self._config

    def annotate(self, result: JobResult) -> Dict[str, Any]:
        """Return a dict merging result metadata with configured annotations."""
        data: Dict[str, Any] = {
            "job_name": result.job_name,
            "success": result.success,
            "environment": self._config.environment,
            "labels": dict(self._config.labels),
        }
        if self._config.team is not None:
            data["team"] = self._config.team
        if result.error_message:
            data["error_message"] = result.error_message
        return data

    def enrich_labels(self, extra: Dict[str, str]) -> "AlertAnnotator":
        """Return a new annotator whose labels are merged with *extra*."""
        merged = {**self._config.labels, **extra}
        new_cfg = AnnotationConfig(
            labels=merged,
            environment=self._config.environment,
            team=self._config.team,
        )
        return AlertAnnotator(new_cfg)
