"""Tests for pipewatch.alerting.suppression."""

from datetime import datetime, time

import pytest

from pipewatch.alerting.suppression import (
    SuppressionSchedule,
    SuppressionWindow,
    _parse_time,
)


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------


def test_parse_time_valid():
    assert _parse_time("08:30") == time(8, 30)


def test_parse_time_single_digit_hour():
    assert _parse_time("9:05") == time(9, 5)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError, match="Invalid time format"):
        _parse_time("not-a-time")


# ---------------------------------------------------------------------------
# SuppressionWindow.is_active
# ---------------------------------------------------------------------------


def _dt(hour: int, minute: int = 0, weekday: int = 0) -> datetime:
    """Create a datetime on a Monday (weekday=0) by default."""
    # 2024-01-01 is a Monday
    base = datetime(2024, 1, 1 + weekday, hour, minute)
    return base


class TestSuppressionWindow:
    def test_active_within_window(self):
        w = SuppressionWindow(start=time(2, 0), end=time(4, 0))
        assert w.is_active(_dt(3, 0)) is True

    def test_inactive_outside_window(self):
        w = SuppressionWindow(start=time(2, 0), end=time(4, 0))
        assert w.is_active(_dt(5, 0)) is False

    def test_overnight_window_before_midnight(self):
        w = SuppressionWindow(start=time(22, 0), end=time(6, 0))
        assert w.is_active(_dt(23, 30)) is True

    def test_overnight_window_after_midnight(self):
        w = SuppressionWindow(start=time(22, 0), end=time(6, 0))
        assert w.is_active(_dt(3, 0)) is True

    def test_inactive_on_excluded_day(self):
        w = SuppressionWindow(start=time(2, 0), end=time(4, 0), days=[1, 2])  # Tue/Wed
        assert w.is_active(_dt(3, 0, weekday=0)) is False  # Monday

    def test_active_on_included_day(self):
        w = SuppressionWindow(start=time(2, 0), end=time(4, 0), days=[0])  # Monday
        assert w.is_active(_dt(3, 0, weekday=0)) is True


# ---------------------------------------------------------------------------
# SuppressionSchedule
# ---------------------------------------------------------------------------


class TestSuppressionSchedule:
    def test_not_suppressed_with_no_windows(self):
        schedule = SuppressionSchedule()
        assert schedule.is_suppressed() is False

    def test_suppressed_when_window_active(self):
        w = SuppressionWindow(start=time(0, 0), end=time(23, 59))
        schedule = SuppressionSchedule([w])
        assert schedule.is_suppressed() is True

    def test_from_config_builds_windows(self):
        config = [
            {"start": "02:00", "end": "04:00", "label": "nightly"},
        ]
        schedule = SuppressionSchedule.from_config(config)
        assert len(schedule.windows) == 1
        assert schedule.windows[0].label == "nightly"
        assert schedule.windows[0].start == time(2, 0)

    def test_from_config_custom_days(self):
        config = [{"start": "10:00", "end": "11:00", "days": [5, 6]}]
        schedule = SuppressionSchedule.from_config(config)
        assert schedule.windows[0].days == [5, 6]
