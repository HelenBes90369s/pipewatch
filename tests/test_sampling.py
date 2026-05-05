"""Tests for pipewatch.alerting.sampling."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.sampling import (
    AlertSampler,
    SampledAlertDispatcher,
    SamplingConfig,
)
from pipewatch.monitor import JobResult


def _make_result(success: bool = True) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.success = success
    return r


# ---------------------------------------------------------------------------
# SamplingConfig
# ---------------------------------------------------------------------------

class TestSamplingConfig:
    def test_defaults(self):
        cfg = SamplingConfig()
        assert cfg.rate == 1.0
        assert cfg.always_send_failures is True
        assert cfg.seed is None

    def test_invalid_rate_below_zero(self):
        with pytest.raises(ValueError):
            SamplingConfig(rate=-0.1)

    def test_invalid_rate_above_one(self):
        with pytest.raises(ValueError):
            SamplingConfig(rate=1.1)

    def test_boundary_values_accepted(self):
        assert SamplingConfig(rate=0.0).rate == 0.0
        assert SamplingConfig(rate=1.0).rate == 1.0


# ---------------------------------------------------------------------------
# AlertSampler
# ---------------------------------------------------------------------------

class TestAlertSampler:
    def test_rate_one_always_sends(self):
        sampler = AlertSampler(SamplingConfig(rate=1.0, always_send_failures=False))
        for _ in range(20):
            assert sampler.should_send(_make_result(success=True)) is True

    def test_rate_zero_never_sends_success(self):
        sampler = AlertSampler(SamplingConfig(rate=0.0, always_send_failures=False))
        for _ in range(20):
            assert sampler.should_send(_make_result(success=True)) is False

    def test_always_send_failures_overrides_zero_rate(self):
        sampler = AlertSampler(SamplingConfig(rate=0.0, always_send_failures=True))
        assert sampler.should_send(_make_result(success=False)) is True

    def test_failures_suppressed_when_flag_off(self):
        sampler = AlertSampler(SamplingConfig(rate=0.0, always_send_failures=False))
        assert sampler.should_send(_make_result(success=False)) is False

    def test_seed_produces_reproducible_results(self):
        cfg = SamplingConfig(rate=0.5, always_send_failures=False, seed=42)
        s1 = AlertSampler(cfg)
        s2 = AlertSampler(cfg)
        results_1 = [s1.should_send(_make_result()) for _ in range(10)]
        results_2 = [s2.should_send(_make_result()) for _ in range(10)]
        assert results_1 == results_2


# ---------------------------------------------------------------------------
# SampledAlertDispatcher
# ---------------------------------------------------------------------------

class TestSampledAlertDispatcher:
    def _make_dispatcher(self, rate=1.0, always_failures=True, seed=0):
        inner = MagicMock()
        cfg = SamplingConfig(rate=rate, always_send_failures=always_failures, seed=seed)
        sampler = AlertSampler(cfg)
        dispatcher = SampledAlertDispatcher(inner, sampler)
        return dispatcher, inner

    def test_forwards_when_sampled_in(self):
        dispatcher, inner = self._make_dispatcher(rate=1.0)
        result = _make_result(success=True)
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once_with(result, None)

    def test_suppresses_when_sampled_out(self):
        dispatcher, inner = self._make_dispatcher(rate=0.0, always_failures=False)
        dispatcher.dispatch(_make_result(success=True))
        inner.dispatch.assert_not_called()

    def test_failure_forwarded_despite_zero_rate(self):
        dispatcher, inner = self._make_dispatcher(rate=0.0, always_failures=True)
        result = _make_result(success=False)
        dispatcher.dispatch(result)
        inner.dispatch.assert_called_once_with(result, None)

    def test_history_passed_through(self):
        dispatcher, inner = self._make_dispatcher(rate=1.0)
        result = _make_result()
        history = MagicMock()
        dispatcher.dispatch(result, history)
        inner.dispatch.assert_called_once_with(result, history)
