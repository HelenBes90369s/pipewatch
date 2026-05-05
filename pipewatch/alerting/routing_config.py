"""Build an AlertRouter from the PipewatchConfig routing section."""
from __future__ import annotations

from typing import Dict, List

from pipewatch.alerting.routing import AlertRouter, RoutingRule
from pipewatch.notifiers import BaseNotifier


def build_router(
    routing_config: List[Dict],
    fallback_notifier_names: List[str] | None = None,
) -> AlertRouter:
    """Construct an :class:`AlertRouter` from a list of rule dicts.

    Each dict may contain:
      - ``pattern``        (str, required)  — glob matched against job name
      - ``notifiers``      (list[str])      — notifier names to use
      - ``tags``           (list[str])      — optional tag filter

    Example YAML::

        routing:
          - pattern: "etl_*"
            notifiers: [slack_ops]
            tags: [critical]
          - pattern: "*"
            notifiers: [slack_general]
    """
    rules: List[RoutingRule] = []
    for entry in routing_config or []:
        pattern = entry.get("pattern", "*")
        notifier_names = entry.get("notifiers", [])
        tags = entry.get("tags", [])
        rules.append(
            RoutingRule(pattern=pattern, notifier_names=notifier_names, tags=tags)
        )
    return AlertRouter(rules=rules, fallback_notifier_names=fallback_notifier_names or [])
