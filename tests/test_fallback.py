"""Tests for FallbackAlertDispatcher and build_fallback_dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerting.fallback import FallbackAlertDispatcher
from pipewatch.alerting.fallback_config import build_fallback_dispatcher
from pipewatch.monitor import JobResult


def _make_result(success: bool = True) -> JobResult:
    r = MagicMock(spec=JobResult)
    r.success = success
    r.job_name = "etl_job"
    return r


def _make_dispatcher(raises: bool = False) -> MagicMock:
    d = MagicMock()
    if raises:
        d.dispatch.side_effect = RuntimeError("send failed")
    return d


# ---------------------------------------------------------------------------
# FallbackAlertDispatcher
# ---------------------------------------------------------------------------

class TestFallbackAlertDispatcher:
    def _make(self, primary, fallbacks=None):
        return FallbackAlertDispatcher(
            _primary=primary, _fallbacks=fallbacks or []
        )

    def test_primary_called_on_success(self):
        primary = _make_dispatcher(raises=False)
        result = _make_result()
        dispatcher = self._make(primary)
        dispatcher.dispatch(result)
        primary.dispatch.assert_called_once_with(result)

    def test_fallback_not_called_when_primary_succeeds(self):
        primary = _make_dispatcher(raises=False)
        fallback = _make_dispatcher(raises=False)
        dispatcher = self._make(primary, [fallback])
        dispatcher.dispatch(_make_result())
        fallback.dispatch.assert_not_called()

    def test_fallback_called_when_primary_fails(self):
        primary = _make_dispatcher(raises=True)
        fallback = _make_dispatcher(raises=False)
        dispatcher = self._make(primary, [fallback])
        dispatcher.dispatch(_make_result())
        fallback.dispatch.assert_called_once()

    def test_second_fallback_called_when_first_fails(self):
        primary = _make_dispatcher(raises=True)
        fb1 = _make_dispatcher(raises=True)
        fb2 = _make_dispatcher(raises=False)
        dispatcher = self._make(primary, [fb1, fb2])
        dispatcher.dispatch(_make_result())
        fb2.dispatch.assert_called_once()

    def test_raises_when_all_fail(self):
        primary = _make_dispatcher(raises=True)
        fb = _make_dispatcher(raises=True)
        dispatcher = self._make(primary, [fb])
        with pytest.raises(RuntimeError, match="send failed"):
            dispatcher.dispatch(_make_result())

    def test_primary_property(self):
        primary = _make_dispatcher()
        dispatcher = self._make(primary)
        assert dispatcher.primary is primary

    def test_fallbacks_property_returns_copy(self):
        fb = _make_dispatcher()
        dispatcher = self._make(_make_dispatcher(), [fb])
        result = dispatcher.fallbacks
        assert result == [fb]
        result.clear()
        assert len(dispatcher.fallbacks) == 1  # original unchanged


# ---------------------------------------------------------------------------
# build_fallback_dispatcher
# ---------------------------------------------------------------------------

class TestBuildFallbackDispatcher:
    def test_builds_with_known_notifiers(self):
        primary = _make_dispatcher()
        fallback = _make_dispatcher()
        notifiers = {"slack": primary, "email": fallback}
        d = build_fallback_dispatcher("slack", ["email"], notifiers)
        assert d.primary is primary
        assert d.fallbacks == [fallback]

    def test_unknown_fallback_name_skipped(self):
        primary = _make_dispatcher()
        notifiers = {"slack": primary}
        d = build_fallback_dispatcher("slack", ["missing"], notifiers)
        assert d.fallbacks == []

    def test_unknown_primary_raises(self):
        with pytest.raises(ValueError, match="Primary notifier"):
            build_fallback_dispatcher("missing", [], {"slack": _make_dispatcher()})

    def test_multiple_fallbacks_ordered(self):
        primary = _make_dispatcher()
        fb1 = _make_dispatcher()
        fb2 = _make_dispatcher()
        notifiers = {"a": primary, "b": fb1, "c": fb2}
        d = build_fallback_dispatcher("a", ["b", "c"], notifiers)
        assert d.fallbacks == [fb1, fb2]
