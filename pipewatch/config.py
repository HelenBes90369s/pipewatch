"""Configuration loader for pipewatch.

Loads settings from environment variables and/or a YAML config file.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class SlackConfig:
    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    username: str = "pipewatch"


@dataclass
class EmailConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: list = field(default_factory=list)
    use_tls: bool = True


@dataclass
class PipewatchConfig:
    job_name: str = "unnamed-job"
    timeout_seconds: Optional[int] = None
    alert_on_failure: bool = True
    alert_on_success: bool = False
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)


def load_config(config_path: Optional[str] = None) -> PipewatchConfig:
    """Load configuration from environment variables and optional YAML file."""
    raw: dict = {}

    if config_path and yaml:
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f) or {}
    elif config_path and not yaml:
        raise ImportError("PyYAML is required to load a config file: pip install pyyaml")

    slack = SlackConfig(
        webhook_url=os.environ.get("PIPEWATCH_SLACK_WEBHOOK", raw.get("slack", {}).get("webhook_url")),
        channel=os.environ.get("PIPEWATCH_SLACK_CHANNEL", raw.get("slack", {}).get("channel")),
        username=os.environ.get("PIPEWATCH_SLACK_USERNAME", raw.get("slack", {}).get("username", "pipewatch")),
    )

    email_raw = raw.get("email", {})
    email = EmailConfig(
        smtp_host=os.environ.get("PIPEWATCH_SMTP_HOST", email_raw.get("smtp_host", "localhost")),
        smtp_port=int(os.environ.get("PIPEWATCH_SMTP_PORT", email_raw.get("smtp_port", 587))),
        smtp_user=os.environ.get("PIPEWATCH_SMTP_USER", email_raw.get("smtp_user")),
        smtp_password=os.environ.get("PIPEWATCH_SMTP_PASSWORD", email_raw.get("smtp_password")),
        from_address=os.environ.get("PIPEWATCH_EMAIL_FROM", email_raw.get("from_address")),
        to_addresses=email_raw.get("to_addresses", []),
        use_tls=email_raw.get("use_tls", True),
    )

    return PipewatchConfig(
        job_name=os.environ.get("PIPEWATCH_JOB_NAME", raw.get("job_name", "unnamed-job")),
        timeout_seconds=int(t) if (t := os.environ.get("PIPEWATCH_TIMEOUT", raw.get("timeout_seconds"))) else None,
        alert_on_failure=raw.get("alert_on_failure", True),
        alert_on_success=raw.get("alert_on_success", False),
        slack=slack,
        email=email,
    )
