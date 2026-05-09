"""Tests for pipewatch.alerting.audit."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.audit import AlertAuditLog, AuditEntry
from pipewatch.monitor import JobResult


def _make_result(success: bool = True, job_name: str = "etl_job") -> JobResult:
    r = MagicMock(spec=JobResult)
    r.job_name = job_name
    r.success = success
    return r


class TestAuditEntry:
    def test_to_dict_keys(self):
        entry = AuditEntry(
            job_name="my_job",
            success=True,
            alert_sent=False,
            notifier="slack",
            reason="no failure",
        )
        d = entry.to_dict()
        assert set(d.keys()) == {
            "job_name", "success", "alert_sent", "notifier", "reason", "timestamp"
        }

    def test_to_dict_values(self):
        entry = AuditEntry(
            job_name="my_job",
            success=False,
            alert_sent=True,
            notifier="email",
            reason="failure detected",
        )
        d = entry.to_dict()
        assert d["job_name"] == "my_job"
        assert d["success"] is False
        assert d["alert_sent"] is True
        assert d["notifier"] == "email"
        assert d["reason"] == "failure detected"

    def test_from_result_populates_fields(self):
        result = _make_result(success=False, job_name="pipeline_x")
        entry = AuditEntry.from_result(
            result, alert_sent=True, notifier="slack", reason="job failed"
        )
        assert entry.job_name == "pipeline_x"
        assert entry.success is False
        assert entry.alert_sent is True
        assert entry.notifier == "slack"
        assert entry.reason == "job failed"

    def test_timestamp_is_utc(self):
        entry = AuditEntry(
            job_name="j", success=True, alert_sent=False, notifier="n", reason="r"
        )
        assert entry.timestamp.tzinfo is not None


class TestAlertAuditLog:
    def test_record_creates_file(self, tmp_path):
        log = AlertAuditLog(str(tmp_path / "audit.jsonl"))
        entry = AuditEntry(
            job_name="j", success=True, alert_sent=False, notifier="slack", reason="ok"
        )
        log.record(entry)
        assert log.path.exists()

    def test_record_and_read_roundtrip(self, tmp_path):
        log = AlertAuditLog(str(tmp_path / "audit.jsonl"))
        entry = AuditEntry(
            job_name="etl", success=False, alert_sent=True, notifier="email", reason="fail"
        )
        log.record(entry)
        entries = log.read_all()
        assert len(entries) == 1
        assert entries[0].job_name == "etl"
        assert entries[0].alert_sent is True

    def test_read_all_empty_when_no_file(self, tmp_path):
        log = AlertAuditLog(str(tmp_path / "missing.jsonl"))
        assert log.read_all() == []

    def test_multiple_entries_preserved(self, tmp_path):
        log = AlertAuditLog(str(tmp_path / "audit.jsonl"))
        for i in range(3):
            log.record(
                AuditEntry(
                    job_name=f"job_{i}",
                    success=i % 2 == 0,
                    alert_sent=True,
                    notifier="slack",
                    reason="test",
                )
            )
        entries = log.read_all()
        assert len(entries) == 3
        assert entries[1].job_name == "job_1"

    def test_malformed_line_is_skipped(self, tmp_path):
        audit_path = tmp_path / "audit.jsonl"
        audit_path.write_text('{"bad": true}\n{"job_name": "ok", "success": true, "alert_sent": false, "notifier": "n", "reason": "r", "timestamp": "2024-01-01T00:00:00+00:00"}\n')
        log = AlertAuditLog(str(audit_path))
        entries = log.read_all()
        assert len(entries) == 1
        assert entries[0].job_name == "ok"

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "audit.jsonl"
        log = AlertAuditLog(str(nested))
        log.record(
            AuditEntry(
                job_name="j", success=True, alert_sent=False, notifier="n", reason="r"
            )
        )
        assert nested.exists()
