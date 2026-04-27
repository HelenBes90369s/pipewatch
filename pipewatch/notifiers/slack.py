"""Slack notifier for pipewatch alerts."""

import logging
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

from pipewatch.config import SlackConfig

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Sends alert messages to a Slack channel via webhook."""

    def __init__(self, config: SlackConfig):
        self.config = config

    def _build_payload(self, message: str, level: str = "info") -> dict:
        emoji = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":red_circle:",
        }.get(level, ":bell:")

        text = f"{emoji} *[pipewatch]* {message}"
        if self.config.channel:
            return {"channel": self.config.channel, "text": text}
        return {"text": text}

    def send(self, message: str, level: str = "info") -> bool:
        """Send a message to Slack. Returns True on success."""
        if not self.config.webhook_url:
            logger.warning("Slack webhook URL not configured; skipping notification.")
            return False

        if requests is None:
            raise RuntimeError("'requests' package is required for Slack notifications.")

        payload = self._build_payload(message, level)
        try:
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            logger.debug("Slack notification sent successfully.")
            return True
        except requests.RequestException as exc:
            logger.error("Failed to send Slack notification: %s", exc)
            return False
