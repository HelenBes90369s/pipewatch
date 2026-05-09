"""Tests for AlertAnnotator and AnnotatedAlertDispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.annotation import AnnotationConfig, AlertAnnotator
from pipewatch.alerting.annotated_dispatcher import AnnotatedAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(success: bool = True, error: str | None = None) -> JobResult:
    return JobResult(
        job_name="pipe.test",
        success=success,
        error_message=error,
        duration_seconds=1.5,
    )


# ---------------------------------------------------------------------------
# AnnotationConfig
# ---------------------------------------------------------------------------

class TestAnnotationConfig:
    def test_defaults(self):
        cfg = AnnotationConfig()
        assert cfg.environment == "production"
        assert cfg.team is None
        assert cfg.labels == {}

    def test_custom_values(self):
        cfg = AnnotationConfig(labels={"region": "us-east"}, environment="staging", team="data")
        assert cfg.labels["region"] == "us-east"
        assert cfg.environment == "staging"
        assert cfg.team == "data"


# ---------------------------------------------------------------------------
# AlertAnnotator
# ---------------------------------------------------------------------------

class TestAlertAnnotator:
    def _make_annotator(self, **kwargs) -> AlertAnnotator:
        return AlertAnnotator(AnnotationConfig(**kwargs))

    def test_annotate_contains_job_name(self):
        ann = self._make_annotator()
        data = ann.annotate(_make_result())
        assert data["job_name"] == "pipe.test"

    def test_annotate_success_flag(self):
        ann = self._make_annotator()
        assert ann.annotate(_make_result(success=True))["success"] is True
        assert ann.annotate(_make_result(success=False))["success"] is False

    def test_annotate_includes_environment(self):
        ann = self._make_annotator(environment="staging")
        assert ann.annotate(_make_result())["environment"] == "staging"

    def test_annotate_team_absent_when_none(self):
        ann = self._make_annotator(team=None)
        assert "team" not in ann.annotate(_make_result())

    def test_annotate_team_present_when_set(self):
        ann = self._make_annotator(team="infra")
        assert ann.annotate(_make_result())["team"] == "infra"

    def test_annotate_error_message_included_on_failure(self):
        ann = self._make_annotator()
        data = ann.annotate(_make_result(success=False, error="boom"))
        assert data["error_message"] == "boom"

    def test_annotate_error_message_absent_on_success(self):
        ann = self._make_annotator()
        assert "error_message" not in ann.annotate(_make_result(success=True))

    def test_enrich_labels_merges(self):
        ann = self._make_annotator(labels={"a": "1"})
        enriched = ann.enrich_labels({"b": "2"})
        data = enriched.annotate(_make_result())
        assert data["labels"] == {"a": "1", "b": "2"}

    def test_enrich_labels_does_not_mutate_original(self):
        ann = self._make_annotator(labels={"a": "1"})
        ann.enrich_labels({"b": "2"})
        assert ann.config.labels == {"a": "1"}


# ---------------------------------------------------------------------------
# AnnotatedAlertDispatcher
# ---------------------------------------------------------------------------

class TestAnnotatedAlertDispatcher:
    def _make(self, **kwargs):
        inner = MagicMock()
        annotator = AlertAnnotator(AnnotationConfig(**kwargs))
        dispatcher = AnnotatedAlertDispatcher(inner, annotator)
        return dispatcher, inner

    def test_inner_dispatch_called(self):
        dispatcher, inner = self._make()
        result = _make_result()
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once_with(result)

    def test_last_annotation_populated_after_dispatch(self):
        dispatcher, _ = self._make(environment="test")
        dispatcher.dispatch(_make_result())
        assert dispatcher.last_annotation["environment"] == "test"

    def test_last_annotation_empty_before_dispatch(self):
        dispatcher, _ = self._make()
        assert dispatcher.last_annotation == {}

    def test_last_annotation_returns_copy(self):
        dispatcher, _ = self._make()
        dispatcher.dispatch(_make_result())
        ann = dispatcher.last_annotation
        ann["injected"] = True
        assert "injected" not in dispatcher.last_annotation
