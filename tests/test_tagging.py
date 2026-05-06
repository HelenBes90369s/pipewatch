"""Tests for pipewatch.alerting.tagging."""
from __future__ import annotations

import pytest

from pipewatch.alerting.tagging import TagFilter, TagRegistry
from pipewatch.monitor import JobResult


def _make_result(tags: list[str] | None = None) -> JobResult:
    r = JobResult(job_name="pipe", success=True)
    r.tags = tags or []
    return r


# ---------------------------------------------------------------------------
# TagFilter
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_empty_filter_matches_everything(self):
        f = TagFilter()
        assert f.matches(_make_result(["a", "b"]))

    def test_empty_filter_matches_no_tags(self):
        assert TagFilter().matches(_make_result([]))

    def test_required_tag_present(self):
        f = TagFilter(required=["env:prod"])
        assert f.matches(_make_result(["env:prod", "team:data"]))

    def test_required_tag_missing(self):
        f = TagFilter(required=["env:prod"])
        assert not f.matches(_make_result(["env:staging"]))

    def test_excluded_tag_absent(self):
        f = TagFilter(excluded=["skip-alerts"])
        assert f.matches(_make_result(["team:data"]))

    def test_excluded_tag_present(self):
        f = TagFilter(excluded=["skip-alerts"])
        assert not f.matches(_make_result(["skip-alerts"]))

    def test_glob_wildcard_in_required(self):
        f = TagFilter(required=["env:*"])
        assert f.matches(_make_result(["env:prod"]))
        assert not f.matches(_make_result(["team:data"]))

    def test_glob_wildcard_in_excluded(self):
        f = TagFilter(excluded=["skip-*"])
        assert not f.matches(_make_result(["skip-alerts"]))
        assert f.matches(_make_result(["send-alerts"]))

    def test_combined_required_and_excluded(self):
        f = TagFilter(required=["env:prod"], excluded=["skip-alerts"])
        assert f.matches(_make_result(["env:prod", "team:data"]))
        assert not f.matches(_make_result(["env:prod", "skip-alerts"]))
        assert not f.matches(_make_result(["env:staging"]))


# ---------------------------------------------------------------------------
# TagRegistry
# ---------------------------------------------------------------------------

class TestTagRegistry:
    def test_register_and_known_tags(self):
        reg = TagRegistry()
        reg.register("env:prod", "team:data")
        assert "env:prod" in reg.known_tags
        assert "team:data" in reg.known_tags

    def test_unknown_tags_empty_when_all_registered(self):
        reg = TagRegistry()
        reg.register("env:prod")
        result = _make_result(["env:prod"])
        assert reg.unknown_tags(result) == []

    def test_unknown_tags_returns_unregistered(self):
        reg = TagRegistry()
        reg.register("env:prod")
        result = _make_result(["env:prod", "mystery-tag"])
        assert reg.unknown_tags(result) == ["mystery-tag"]

    def test_no_tags_on_result(self):
        reg = TagRegistry()
        reg.register("env:prod")
        result = _make_result([])
        assert reg.unknown_tags(result) == []
