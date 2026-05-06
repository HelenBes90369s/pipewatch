"""Build a PriorityAlertDispatcher from config dictionaries."""
from __future__ import annotations

from typing import Any, Dict, List

from pipewatch.alerting.priority import Priority, PriorityClassifier, PriorityRule
from pipewatch.alerting.priority_dispatcher import PriorityAlertDispatcher


def _parse_priority(value: str) -> Priority:
    try:
        return Priority(value.lower())
    except ValueError:
        raise ValueError(f"Unknown priority level: {value!r}")


def build_priority_dispatcher(
    rules_cfg: List[Dict[str, Any]],
    notifiers_cfg: List[Dict[str, Any]],
    named_notifiers: Dict[str, Any],
    *,
    default_priority: str = "medium",
    exact_match: bool = False,
) -> PriorityAlertDispatcher:
    """Construct a :class:`PriorityAlertDispatcher` from plain config dicts.

    ``rules_cfg`` entries::

        [{"priority": "high", "job_name": "etl_load", "on_failure": true}]

    ``notifiers_cfg`` entries::

        [{"name": "slack_ops", "priority": "high"}]
    """
    rules: List[PriorityRule] = []
    for entry in rules_cfg:
        rules.append(
            PriorityRule(
                priority=_parse_priority(entry["priority"]),
                job_name=entry.get("job_name"),
                min_duration_seconds=entry.get("min_duration_seconds"),
                on_failure=entry.get("on_failure", True),
                on_success=entry.get("on_success", False),
            )
        )

    classifier = PriorityClassifier(
        rules=rules,
        default_priority=_parse_priority(default_priority),
    )
    dispatcher = PriorityAlertDispatcher(classifier=classifier, exact_match=exact_match)

    for entry in notifiers_cfg:
        name = entry.get("name", "")
        if name not in named_notifiers:
            continue
        priority = _parse_priority(entry.get("priority", default_priority))
        dispatcher.register(named_notifiers[name], priority)

    return dispatcher
