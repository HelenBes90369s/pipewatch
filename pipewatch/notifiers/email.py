"""Email notifier for pipewatch alerts."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from pipewatch.config import EmailConfig

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends alert messages via SMTP email."""

    def __init__(self, config: EmailConfig):
        self.config = config

    def _build_message(self, subject: str, body: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = self.config.sender
        msg["To"] = ", ".join(self.config.recipients)
        msg["Subject"] = f"[pipewatch] {subject}"
        msg.attach(MIMEText(body, "plain"))
        return msg

    def send(self, subject: str, body: str) -> bool:
        """Send an email alert. Returns True on success."""
        if not self.config.recipients:
            logger.warning("No email recipients configured; skipping notification.")
            return False

        msg = self._build_message(subject, body)
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port,
                              timeout=self.config.timeout_seconds) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)
                server.sendmail(
                    self.config.sender,
                    self.config.recipients,
                    msg.as_string(),
                )
            logger.debug("Email notification sent to %s.", self.config.recipients)
            return True
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send email notification: %s", exc)
            return False
