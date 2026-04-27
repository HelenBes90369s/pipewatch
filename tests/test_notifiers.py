"""Tests for Slack and Email notifiers."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from pipewatch.config import SlackConfig, EmailConfig
from pipewatch.notifiers.slack import SlackNotifier
from pipewatch.notifiers.email import EmailNotifier


# ---------------------------------------------------------------------------
# SlackNotifier tests
# ---------------------------------------------------------------------------

class TestSlackNotifier:
    def _make_notifier(self, webhook_url="https://hooks.slack.com/test", channel="#alerts"):
        config = SlackConfig(webhook_url=webhook_url, channel=channel)
        return SlackNotifier(config)

    def test_send_returns_false_when_no_webhook(self):
        config = SlackConfig(webhook_url=None)
        notifier = SlackNotifier(config)
        assert notifier.send("hello") is False

    def test_build_payload_includes_channel(self):
        notifier = self._make_notifier(channel="#ops")
        payload = notifier._build_payload("test message", level="error")
        assert payload["channel"] == "#ops"
        assert "pipewatch" in payload["text"]
        assert ":red_circle:" in payload["text"]

    def test_build_payload_no_channel(self):
        notifier = self._make_notifier(channel=None)
        payload = notifier._build_payload("msg")
        assert "channel" not in payload

    @patch("pipewatch.notifiers.slack.requests")
    def test_send_success(self, mock_requests):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response

        notifier = self._make_notifier()
        result = notifier.send("pipeline finished", level="info")

        assert result is True
        mock_requests.post.assert_called_once()

    @patch("pipewatch.notifiers.slack.requests")
    def test_send_failure_returns_false(self, mock_requests):
        mock_requests.RequestException = Exception
        mock_requests.post.side_effect = Exception("connection error")

        notifier = self._make_notifier()
        result = notifier.send("oops")
        assert result is False


# ---------------------------------------------------------------------------
# EmailNotifier tests
# ---------------------------------------------------------------------------

class TestEmailNotifier:
    def _make_notifier(self, recipients=None):
        config = EmailConfig(
            smtp_host="localhost",
            smtp_port=25,
            sender="pipewatch@example.com",
            recipients=recipients or ["ops@example.com"],
            use_tls=False,
        )
        return EmailNotifier(config)

    def test_send_returns_false_when_no_recipients(self):
        notifier = self._make_notifier(recipients=[])
        assert notifier.send("subject", "body") is False

    def test_build_message_subject_prefix(self):
        notifier = self._make_notifier()
        msg = notifier._build_message("Job failed", "Details here")
        assert msg["Subject"] == "[pipewatch] Job failed"
        assert msg["From"] == "pipewatch@example.com"

    @patch("pipewatch.notifiers.email.smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

        notifier = self._make_notifier()
        result = notifier.send("Alert", "Something went wrong.")

        assert result is True
        mock_smtp.sendmail.assert_called_once()

    @patch("pipewatch.notifiers.email.smtplib.SMTP")
    def test_send_smtp_error_returns_false(self, mock_smtp_cls):
        mock_smtp_cls.side_effect = smtplib.SMTPException("refused")

        notifier = self._make_notifier()
        result = notifier.send("Alert", "body")
        assert result is False
