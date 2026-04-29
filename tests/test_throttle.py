"""Tests for alert throttling."""

from datetime import datetime, timedelta

import pytest

from pipewatch.alerting.throttle import AlertThrottle, ThrottleConfig


class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.min_interval_seconds == 300
        assert cfg.max_alerts_per_hour == 10

    def test_custom_values(self):
        cfg = ThrottleConfig(min_interval_seconds=60, max_alerts_per_hour=3)
        assert cfg.min_interval_seconds == 60
        assert cfg.max_alerts_per_hour == 3


class TestAlertThrottle:
    def _make_throttle(self, interval=10, max_per_hour=5):
        return AlertThrottle(ThrottleConfig(
            min_interval_seconds=interval,
            max_alerts_per_hour=max_per_hour,
        ))

    def test_first_alert_always_allowed(self):
        throttle = self._make_throttle()
        assert throttle.should_send("my_job") is True

    def test_second_alert_blocked_within_interval(self):
        throttle = self._make_throttle(interval=300)
        throttle.record("my_job")
        assert throttle.should_send("my_job") is False

    def test_second_alert_allowed_after_interval(self):
        throttle = self._make_throttle(interval=0)
        throttle.record("my_job")
        assert throttle.should_send("my_job") is True

    def test_different_jobs_are_independent(self):
        throttle = self._make_throttle(interval=300)
        throttle.record("job_a")
        assert throttle.should_send("job_b") is True

    def test_rate_limit_blocks_after_max(self):
        throttle = self._make_throttle(interval=0, max_per_hour=3)
        for _ in range(3):
            throttle.record("my_job")
        assert throttle.should_send("my_job") is False

    def test_old_alerts_not_counted_in_rate(self):
        throttle = self._make_throttle(interval=0, max_per_hour=2)
        old_time = datetime.utcnow() - timedelta(hours=2)
        throttle._alert_counts["my_job"] = [old_time, old_time]
        throttle._last_alert["my_job"] = old_time
        assert throttle.should_send("my_job") is True

    def test_record_updates_last_alert(self):
        throttle = self._make_throttle()
        assert "my_job" not in throttle._last_alert
        throttle.record("my_job")
        assert "my_job" in throttle._last_alert
