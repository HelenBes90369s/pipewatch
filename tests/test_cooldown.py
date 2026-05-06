"""Tests for pipewatch.alerting.cooldown."""
from __future__ import annotations

import time

import pytest

from pipewatch.alerting.cooldown import AlertCooldown, CooldownConfig


# ---------------------------------------------------------------------------
# CooldownConfig
# ---------------------------------------------------------------------------

class TestCooldownConfig:
    def test_defaults(self):
        cfg = CooldownConfig()
        assert cfg.period_seconds == 300

    def test_custom_period(self):
        cfg = CooldownConfig(period_seconds=60)
        assert cfg.period_seconds == 60

    def test_zero_period_is_valid(self):
        cfg = CooldownConfig(period_seconds=0)
        assert cfg.period_seconds == 0

    def test_negative_period_raises(self):
        with pytest.raises(ValueError, match="period_seconds"):
            CooldownConfig(period_seconds=-1)


# ---------------------------------------------------------------------------
# AlertCooldown
# ---------------------------------------------------------------------------

class TestAlertCooldown:
    def _make_cooldown(self, period: int = 60) -> AlertCooldown:
        return AlertCooldown(CooldownConfig(period_seconds=period))

    def test_should_send_first_time(self):
        cd = self._make_cooldown()
        assert cd.should_send("my_job") is True

    def test_should_not_send_immediately_after_record(self):
        cd = self._make_cooldown(period=60)
        cd.record("my_job")
        assert cd.should_send("my_job") is False

    def test_should_send_after_period_elapsed(self, monkeypatch):
        cd = self._make_cooldown(period=30)
        start = time.monotonic()
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start)
        cd.record("my_job")
        # Advance time beyond the cooldown period
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start + 31)
        assert cd.should_send("my_job") is True

    def test_zero_period_always_sends(self):
        cd = self._make_cooldown(period=0)
        cd.record("my_job")
        assert cd.should_send("my_job") is True

    def test_reset_clears_state(self):
        cd = self._make_cooldown(period=300)
        cd.record("my_job")
        assert cd.should_send("my_job") is False
        cd.reset("my_job")
        assert cd.should_send("my_job") is True

    def test_reset_unknown_job_is_noop(self):
        cd = self._make_cooldown()
        cd.reset("unknown_job")  # should not raise

    def test_remaining_seconds_before_record(self):
        cd = self._make_cooldown(period=60)
        assert cd.remaining_seconds("my_job") == 0.0

    def test_remaining_seconds_after_record(self, monkeypatch):
        cd = self._make_cooldown(period=60)
        start = time.monotonic()
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start)
        cd.record("my_job")
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start + 10)
        assert abs(cd.remaining_seconds("my_job") - 50.0) < 0.1

    def test_remaining_seconds_after_expiry(self, monkeypatch):
        cd = self._make_cooldown(period=30)
        start = time.monotonic()
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start)
        cd.record("my_job")
        monkeypatch.setattr("pipewatch.alerting.cooldown.time.monotonic", lambda: start + 60)
        assert cd.remaining_seconds("my_job") == 0.0

    def test_independent_jobs_tracked_separately(self):
        cd = self._make_cooldown(period=300)
        cd.record("job_a")
        assert cd.should_send("job_a") is False
        assert cd.should_send("job_b") is True
