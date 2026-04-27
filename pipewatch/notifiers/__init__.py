"""Notifier sub-package for pipewatch.

Exposes the concrete notifiers and the retry helper so callers can do::

    from pipewatch.notifiers import SlackNotifier, EmailNotifier, with_retry, RetryConfig
"""

from pipewatch.notifiers.slack import SlackNotifier
from pipewatch.notifiers.email import EmailNotifier
from pipewatch.notifiers.retry import RetryConfig, RetryingNotifier, with_retry

__all__ = [
    "SlackNotifier",
    "EmailNotifier",
    "RetryConfig",
    "RetryingNotifier",
    "with_retry",
]
