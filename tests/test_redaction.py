"""Tests for pipewatch.alerting.redaction and RedactedAlertDispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.redaction import AlertRedactor, RedactionConfig
from pipewatch.alerting.redacted_dispatcher import RedactedAlertDispatcher
from pipewatch.monitor import JobResult


def _make_result(metadata: dict | None = None, success: bool = True) -> JobResult:
    return JobResult(
        job_name="test_job",
        success=success,
        error=None if success else "boom",
        metrics=None,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# RedactionConfig
# ---------------------------------------------------------------------------


class TestRedactionConfig:
    def test_defaults_include_common_patterns(self):
        cfg = RedactionConfig()
        assert cfg.is_sensitive("password")
        assert cfg.is_sensitive("api_key")
        assert cfg.is_sensitive("auth_token")

    def test_case_insensitive_by_default(self):
        cfg = RedactionConfig()
        assert cfg.is_sensitive("PASSWORD")
        assert cfg.is_sensitive("Secret")

    def test_case_sensitive_mode(self):
        cfg = RedactionConfig(patterns=["secret"], case_sensitive=True)
        assert cfg.is_sensitive("secret")
        assert not cfg.is_sensitive("SECRET")

    def test_non_sensitive_key_returns_false(self):
        cfg = RedactionConfig()
        assert not cfg.is_sensitive("job_name")
        assert not cfg.is_sensitive("duration")

    def test_custom_pattern(self):
        cfg = RedactionConfig(patterns=[r"ssn"])
        assert cfg.is_sensitive("user_ssn")
        assert not cfg.is_sensitive("password")  # default not included


# ---------------------------------------------------------------------------
# AlertRedactor
# ---------------------------------------------------------------------------


class TestAlertRedactor:
    def test_redacts_sensitive_key(self):
        redactor = AlertRedactor()
        result = redactor.redact({"password": "hunter2", "job": "etl"})
        assert result["password"] == "[REDACTED]"
        assert result["job"] == "etl"

    def test_redacts_nested_sensitive_key(self):
        redactor = AlertRedactor()
        result = redactor.redact({"db": {"password": "s3cr3t", "host": "localhost"}})
        assert result["db"]["password"] == "[REDACTED]"
        assert result["db"]["host"] == "localhost"

    def test_non_sensitive_values_unchanged(self):
        redactor = AlertRedactor()
        result = redactor.redact({"rows_processed": 1000})
        assert result["rows_processed"] == 1000

    def test_redact_result_includes_job_name(self):
        redactor = AlertRedactor()
        r = _make_result(metadata={"api_key": "abc123", "env": "prod"})
        out = redactor.redact_result(r)
        assert out["job_name"] == "test_job"
        assert out["metadata"]["api_key"] == "[REDACTED]"
        assert out["metadata"]["env"] == "prod"


# ---------------------------------------------------------------------------
# RedactedAlertDispatcher
# ---------------------------------------------------------------------------


class TestRedactedAlertDispatcher:
    def _make_dispatcher(self, metadata=None):
        inner = MagicMock()
        dispatcher = RedactedAlertDispatcher(inner)
        result = _make_result(metadata=metadata)
        return dispatcher, inner, result

    def test_inner_is_called(self):
        dispatcher, inner, result = self._make_dispatcher()
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once()

    def test_sensitive_metadata_redacted_before_dispatch(self):
        dispatcher, inner, result = self._make_dispatcher(
            metadata={"token": "xyz", "rows": 42}
        )
        dispatcher.dispatch(result)
        forwarded: JobResult = inner.dispatch.call_args[0][0]
        assert forwarded.metadata["token"] == "[REDACTED]"
        assert forwarded.metadata["rows"] == 42

    def test_result_without_metadata_passes_through(self):
        inner = MagicMock()
        result = _make_result(metadata=None)
        dispatcher = RedactedAlertDispatcher(inner)
        dispatcher.dispatch(result)
        forwarded: JobResult = inner.dispatch.call_args[0][0]
        assert forwarded.job_name == result.job_name

    def test_exposes_inner_and_redactor(self):
        inner = MagicMock()
        redactor = AlertRedactor(RedactionConfig(patterns=["secret"]))
        d = RedactedAlertDispatcher(inner, redactor)
        assert d.inner is inner
        assert d.redactor is redactor
