"""Build a FallbackAlertDispatcher from config-level notifier mappings."""
from __future__ import annotations

from typing import Any, Dict, List

from pipewatch.alerting.fallback import FallbackAlertDispatcher


def build_fallback_dispatcher(
    primary_name: str,
    fallback_names: List[str],
    notifiers: Dict[str, Any],
) -> FallbackAlertDispatcher:
    """Construct a :class:`FallbackAlertDispatcher` from named notifiers.

    Parameters
    ----------
    primary_name:
        Key into *notifiers* for the primary dispatcher/notifier.
    fallback_names:
        Ordered list of keys into *notifiers* to use as fallbacks.
    notifiers:
        Mapping of name → dispatcher or notifier objects.  Unknown names are
        silently skipped so that optional integrations don't break startup.

    Returns
    -------
    FallbackAlertDispatcher
    """
    primary = notifiers.get(primary_name)
    if primary is None:
        raise ValueError(
            f"Primary notifier {primary_name!r} not found in notifiers map."
        )

    fallbacks = [
        notifiers[name]
        for name in fallback_names
        if name in notifiers
    ]

    return FallbackAlertDispatcher(_primary=primary, _fallbacks=fallbacks)
