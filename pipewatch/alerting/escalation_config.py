"""Load EscalationPolicy from PipewatchConfig escalation settings."""
from __future__ import annotations

from typing import Any, Dict, List

from pipewatch.alerting.escalation import EscalationLevel, EscalationPolicy
from pipewatch.history import JobHistory
from pipewatch.notifiers import BaseNotifier


def build_escalation_policy(
    escalation_cfg: List[Dict[str, Any]],
    notifier_map: Dict[str, BaseNotifier],
    history: JobHistory,
) -> EscalationPolicy:
    """Construct an EscalationPolicy from raw config dicts.

    Each entry in *escalation_cfg* should look like::

        - min_streak: 3
          notifiers: [slack, email]

    *notifier_map* maps notifier name strings to instantiated notifier objects.
    """
    levels: List[EscalationLevel] = []
    for item in escalation_cfg:
        min_streak = int(item.get("min_streak", 1))
        names: List[str] = item.get("notifiers", [])
        resolved = [notifier_map[n] for n in names if n in notifier_map]
        levels.append(EscalationLevel(min_streak=min_streak, notifiers=resolved))

    if not levels:
        raise ValueError("escalation_cfg must contain at least one level entry.")

    return EscalationPolicy(levels=levels, history=history)
