"""Build a CheckpointAlertDispatcher from config and a notifier registry."""

from __future__ import annotations

from typing import Any, Dict, List

from pipewatch.alerting.checkpoint import CheckpointAlertDispatcher, CheckpointStore
from pipewatch.alerting.dispatcher import AlertDispatcher


def build_checkpoint_dispatcher(
    cfg: Dict[str, Any],
    notifiers: Dict[str, Any],
) -> CheckpointAlertDispatcher:
    """Construct a :class:`CheckpointAlertDispatcher` from a config mapping.

    Expected *cfg* keys:
    - ``notifiers`` (list[str]): names of notifiers to use for the inner dispatcher.

    Unknown keys are silently ignored so callers may pass the full pipeline config.
    """
    notifier_names: List[str] = cfg.get("notifiers", [])
    selected = [notifiers[n] for n in notifier_names if n in notifiers]

    inner = AlertDispatcher(notifiers=selected)
    store = CheckpointStore()
    return CheckpointAlertDispatcher(inner=inner, store=store)
