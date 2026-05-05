"""Tests for pipewatch.alerting.enrichment and enrichment_config."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.enrichment import AlertEnricher, EnrichmentContext
from pipewatch.alerting.enrichment_config import build_enricher
from pipewatch.monitor import JobResult
from pipewatch.metrics import JobMetrics


def _make_result(name: str = "etl_job", success: bool = True, metadata=None) -> JobResult:
    m = JobMetrics(job_name=name)
    m.stop()
    return JobResult(
        job_name=name,
        success=success,
        error=None if success else "boom",
        metrics=m,
        metadata=metadata or {},
    )


class TestEnrichmentContext:
    def test_to_dict_contains_required_keys(self):
        ctx = EnrichmentContext(hostname="host1", pid=42, environment="staging")
        d = ctx.to_dict()
        assert d["hostname"] == "host1"
        assert d["pid"] == 42
        assert d["environment"] == "staging"

    def test_extra_merged_into_dict(self):
        ctx = EnrichmentContext(extra={"team": "data-eng"})
        d = ctx.to_dict()
        assert d["team"] == "data-eng"

    def test_defaults_are_populated(self):
        ctx = EnrichmentContext()
        d = ctx.to_dict()
        assert "hostname" in d
        assert "pid" in d
        assert d["environment"] in ("production", "staging", "test")  # env-dependent


class TestAlertEnricher:
    def _make_enricher(self, **ctx_kwargs):
        inner = MagicMock()
        ctx = EnrichmentContext(**ctx_kwargs)
        return AlertEnricher(inner, context=ctx), inner

    def test_dispatch_calls_inner(self):
        enricher, inner = self._make_enricher(hostname="box", pid=1, environment="prod")
        result = _make_result()
        enricher.dispatch(result)
        inner.dispatch.assert_called_once()

    def test_enriched_result_has_hostname(self):
        enricher, inner = self._make_enricher(hostname="myhost", pid=99, environment="prod")
        result = _make_result()
        enricher.dispatch(result)
        dispatched: JobResult = inner.dispatch.call_args[0][0]
        assert dispatched.metadata["hostname"] == "myhost"

    def test_enriched_result_preserves_original_metadata(self):
        enricher, inner = self._make_enricher(hostname="h", pid=1, environment="prod")
        result = _make_result(metadata={"source": "kafka"})
        enricher.dispatch(result)
        dispatched: JobResult = inner.dispatch.call_args[0][0]
        assert dispatched.metadata["source"] == "kafka"

    def test_original_result_not_mutated(self):
        enricher, _ = self._make_enricher(hostname="h", pid=1, environment="prod")
        result = _make_result(metadata={})
        enricher.dispatch(result)
        assert "hostname" not in result.metadata

    def test_context_property(self):
        ctx = EnrichmentContext(environment="staging")
        enricher = AlertEnricher(MagicMock(), context=ctx)
        assert enricher.context is ctx


class TestBuildEnricher:
    def test_empty_config_returns_enricher(self):
        inner = MagicMock()
        enricher = build_enricher(inner, {})
        assert isinstance(enricher, AlertEnricher)

    def test_none_config_returns_enricher(self):
        inner = MagicMock()
        enricher = build_enricher(inner, None)
        assert isinstance(enricher, AlertEnricher)

    def test_environment_passed_through(self):
        inner = MagicMock()
        enricher = build_enricher(inner, {"environment": "staging"})
        assert enricher.context.environment == "staging"

    def test_extra_labels_passed_through(self):
        inner = MagicMock()
        enricher = build_enricher(inner, {"extra": {"region": "eu-west-1"}})
        assert enricher.context.extra["region"] == "eu-west-1"
