"""Build an AlertEnricher from PipewatchConfig enrichment settings."""
from __future__ import annotations

from typing import Any, Dict

from pipewatch.alerting.enrichment import AlertEnricher, EnrichmentContext


def build_enricher(inner, enrichment_cfg: Dict[str, Any]) -> AlertEnricher:
    """Construct an :class:`AlertEnricher` wrapping *inner* dispatcher.

    *enrichment_cfg* is expected to be the ``enrichment`` sub-dict from the
    loaded YAML / env config, e.g.::

        enrichment:
          environment: staging
          extra:
            team: data-eng
            region: us-east-1

    Unknown keys inside ``extra`` are passed through verbatim so operators can
    attach arbitrary labels without touching source code.
    """
    if not enrichment_cfg:
        return AlertEnricher(inner)

    environment: str = enrichment_cfg.get("environment", "production")
    extra: Dict[str, Any] = enrichment_cfg.get("extra", {}) or {}

    ctx = EnrichmentContext(environment=environment, extra=extra)
    return AlertEnricher(inner, context=ctx)
