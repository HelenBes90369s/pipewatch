"""Tests for pipewatch configuration loading."""

import os
import textwrap
import tempfile
import pytest

from pipewatch.config import load_config, PipewatchConfig, SlackConfig, EmailConfig


def test_defaults_with_no_env_or_file():
    """Config should return sensible defaults when nothing is set."""
    # Clear relevant env vars
    for key in ["PIPEWATCH_JOB_NAME", "PIPEWATCH_SLACK_WEBHOOK", "PIPEWATCH_TIMEOUT"]:
        os.environ.pop(key, None)

    config = load_config()

    assert isinstance(config, PipewatchConfig)
    assert config.job_name == "unnamed-job"
    assert config.timeout_seconds is None
    assert config.alert_on_failure is True
    assert config.alert_on_success is False
    assert config.slack.webhook_url is None
    assert config.email.smtp_port == 587


def test_env_vars_override_defaults(monkeypatch):
    """Environment variables should override defaults."""
    monkeypatch.setenv("PIPEWATCH_JOB_NAME", "my-etl-job")
    monkeypatch.setenv("PIPEWATCH_SLACK_WEBHOOK", "https://hooks.slack.com/test")
    monkeypatch.setenv("PIPEWATCH_SLACK_CHANNEL", "#alerts")
    monkeypatch.setenv("PIPEWATCH_TIMEOUT", "3600")
    monkeypatch.setenv("PIPEWATCH_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("PIPEWATCH_SMTP_PORT", "465")

    config = load_config()

    assert config.job_name == "my-etl-job"
    assert config.slack.webhook_url == "https://hooks.slack.com/test"
    assert config.slack.channel == "#alerts"
    assert config.timeout_seconds == 3600
    assert config.email.smtp_host == "smtp.example.com"
    assert config.email.smtp_port == 465


def test_load_from_yaml_file():
    """Config should load values from a YAML file."""
    pytest.importorskip("yaml")

    yaml_content = textwrap.dedent("""
        job_name: yaml-pipeline
        timeout_seconds: 1800
        alert_on_success: true
        slack:
          webhook_url: https://hooks.slack.com/yaml
          channel: "#pipeline"
        email:
          smtp_host: mail.yaml.com
          smtp_port: 587
          from_address: alerts@yaml.com
          to_addresses:
            - ops@yaml.com
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_config(config_path=tmp_path)
        assert config.job_name == "yaml-pipeline"
        assert config.timeout_seconds == 1800
        assert config.alert_on_success is True
        assert config.slack.webhook_url == "https://hooks.slack.com/yaml"
        assert config.email.smtp_host == "mail.yaml.com"
        assert config.email.to_addresses == ["ops@yaml.com"]
    finally:
        os.unlink(tmp_path)


def test_slack_config_defaults():
    config = SlackConfig()
    assert config.username == "pipewatch"
    assert config.webhook_url is None


def test_email_config_defaults():
    config = EmailConfig()
    assert config.smtp_host == "localhost"
    assert config.use_tls is True
    assert config.to_addresses == []
