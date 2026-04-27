"""Tests for pipewatch.notifiers.retry."""

import pytest
from unittest.mock import MagicMock, patch

from pipewatch.notifiers.retry import RetryConfig, RetryingNotifier, with_retry


# ---------------------------------------------------------------------------
# RetryConfig tests
# ---------------------------------------------------------------------------

class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_attempts == 3
        assert cfg.base_delay == 1.0
        assert cfg.backoff_factor == 2.0

    def test_delay_for_first_attempt_is_zero(self):
        cfg = RetryConfig(base_delay=5.0)
        assert cfg.delay_for(0) == 0.0

    def test_delay_for_second_attempt(self):
        cfg = RetryConfig(base_delay=2.0, backoff_factor=3.0)
        assert cfg.delay_for(1) == 2.0

    def test_delay_for_third_attempt(self):
        cfg = RetryConfig(base_delay=2.0, backoff_factor=3.0)
        assert cfg.delay_for(2) == 6.0

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=0)

    def test_invalid_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay"):
            RetryConfig(base_delay=-1)


# ---------------------------------------------------------------------------
# RetryingNotifier tests
# ---------------------------------------------------------------------------

def _make_notifier(send_results):
    """Return a mock notifier whose send() returns values from *send_results*."""
    notifier = MagicMock()
    notifier.name = "MockNotifier"
    notifier.send.side_effect = send_results
    return notifier


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("pipewatch.notifiers.retry.time.sleep", lambda _: None)


class TestRetryingNotifier:
    def test_success_on_first_attempt(self):
        inner = _make_notifier([True])
        rn = RetryingNotifier(inner, RetryConfig(max_attempts=3))
        assert rn.send(object()) is True
        assert inner.send.call_count == 1

    def test_retries_on_false_and_succeeds(self):
        inner = _make_notifier([False, False, True])
        rn = RetryingNotifier(inner, RetryConfig(max_attempts=3, base_delay=0))
        assert rn.send(object()) is True
        assert inner.send.call_count == 3

    def test_all_attempts_fail_returns_false(self):
        inner = _make_notifier([False, False, False])
        rn = RetryingNotifier(inner, RetryConfig(max_attempts=3, base_delay=0))
        assert rn.send(object()) is False
        assert inner.send.call_count == 3

    def test_exception_treated_as_failure_and_retried(self):
        inner = _make_notifier([RuntimeError("boom"), True])
        rn = RetryingNotifier(inner, RetryConfig(max_attempts=3, base_delay=0))
        assert rn.send(object()) is True
        assert inner.send.call_count == 2

    def test_name_falls_back_to_class_name(self):
        inner = MagicMock(spec=["send"])  # no .name attribute
        rn = RetryingNotifier(inner)
        assert rn.name == "MagicMock"

    def test_with_retry_factory(self):
        inner = _make_notifier([True])
        rn = with_retry(inner)
        assert isinstance(rn, RetryingNotifier)
        assert rn.send(object()) is True
