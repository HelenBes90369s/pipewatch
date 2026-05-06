"""Tests for TaggedAlertDispatcher and build_tagged_dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock

from pipewatch.alerting.tagging import TagFilter
from pipewatch.alerting.tagged_dispatcher import TaggedAlertDispatcher
from pipewatch.alerting.tagging_config import build_tagged_dispatcher
from pipewatch.monitor import JobResult


def _make_result(tags: list[str] | None = None, success: bool = False) -> JobResult:
    r = JobResult(job_name="etl", success=success)
    r.tags = tags or []
    return r


def _make_inner():
    return MagicMock()


class TestTaggedAlertDispatcher:
    def _make_dispatcher(self, required=None, excluded=None):
        inner = _make_inner()
        f = TagFilter(required=required or [], excluded=excluded or [])
        return TaggedAlertDispatcher(inner=inner, tag_filter=f), inner

    def test_dispatches_when_filter_matches(self):
        d, inner = self._make_dispatcher(required=["env:prod"])
        result = _make_result(["env:prod"])
        d.dispatch(result)
        inner.dispatch.assert_called_once_with(result)

    def test_skips_when_filter_does_not_match(self):
        d, inner = self._make_dispatcher(required=["env:prod"])
        result = _make_result(["env:staging"])
        d.dispatch(result)
        inner.dispatch.assert_not_called()

    def test_excluded_tag_prevents_dispatch(self):
        d, inner = self._make_dispatcher(excluded=["skip-alerts"])
        result = _make_result(["skip-alerts"])
        d.dispatch(result)
        inner.dispatch.assert_not_called()

    def test_default_filter_passes_everything(self):
        inner = _make_inner()
        d = TaggedAlertDispatcher(inner=inner)
        d.dispatch(_make_result([]))
        inner.dispatch.assert_called_once()

    def test_filter_property(self):
        f = TagFilter(required=["x"])
        d = TaggedAlertDispatcher(inner=_make_inner(), tag_filter=f)
        assert d.filter is f

    def test_inner_property(self):
        inner = _make_inner()
        d = TaggedAlertDispatcher(inner=inner)
        assert d.inner is inner


class TestBuildTaggedDispatcher:
    def test_builds_with_required_and_excluded(self):
        inner = _make_inner()
        cfg = {"tags": {"required": ["env:prod"], "excluded": ["skip"]}}
        d = build_tagged_dispatcher(inner, cfg)
        assert d.filter.required == ["env:prod"]
        assert d.filter.excluded == ["skip"]

    def test_empty_config_creates_pass_through(self):
        inner = _make_inner()
        d = build_tagged_dispatcher(inner, {})
        assert d.filter.required == []
        assert d.filter.excluded == []

    def test_dispatches_correctly_after_build(self):
        inner = _make_inner()
        cfg = {"tags": {"required": ["team:data"]}}
        d = build_tagged_dispatcher(inner, cfg)
        result = _make_result(["team:data"])
        d.dispatch(result)
        inner.dispatch.assert_called_once_with(result)
