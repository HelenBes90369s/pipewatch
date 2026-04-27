# pipewatch

Lightweight monitoring utility for long-running data pipeline jobs with Slack and email alerting.

---

## Installation

```bash
pip install pipewatch
```

Or install from source:

```bash
git clone https://github.com/yourname/pipewatch.git && cd pipewatch && pip install -e .
```

---

## Usage

Wrap any pipeline job with `pipewatch` to receive alerts on completion, failure, or timeout.

```python
from pipewatch import monitor

@monitor(
    job_name="nightly_etl",
    timeout_minutes=120,
    alert_on=["failure", "timeout"],
    slack_webhook="https://hooks.slack.com/services/...",
    email="ops-team@example.com"
)
def run_pipeline():
    # your long-running pipeline logic here
    load_data()
    transform()
    export()

run_pipeline()
```

You can also use the context manager form:

```python
from pipewatch import watch

with watch("daily_sync", timeout_minutes=60):
    sync_database()
```

Configure credentials via environment variables or a `pipewatch.yaml` config file:

```yaml
slack_webhook: "https://hooks.slack.com/services/..."
email: "alerts@example.com"
default_timeout_minutes: 90
```

---

## License

MIT © 2024 — see [LICENSE](LICENSE) for details.