"""Build a :class:`TaggedAlertDispatcher` from a plain config dict."""
from __future__ import annotations

from typing import Any

from pipewatch.alerting.tagging import TagFilter
from pipewatch.alerting.tagged_dispatcher import TaggedAlertDispatcher


def build_tagged_dispatcher(
    inner,
    config: dict[str, Any],
) -> TaggedAlertDispatcher:
    """Construct a :class:`TaggedAlertDispatcher` from *config*.

    Expected config shape::

        tags:
          required: ["team:data", "env:prod"]
          excluded: ["skip-alerts"]

    Both keys are optional and default to empty lists.

    Parameters
    ----------
    inner:
        The downstream dispatcher to wrap.
    config:
        A dictionary, typically loaded from YAML, containing an optional
        ``tags`` sub-key.
    """
    tags_cfg: dict[str, Any] = config.get("tags", {})
    tag_filter = TagFilter(
        required=list(tags_cfg.get("required", [])),
        excluded=list(tags_cfg.get("excluded", [])),
    )
    return TaggedAlertDispatcher(inner=inner, tag_filter=tag_filter)
