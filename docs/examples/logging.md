# Logging — Examples

Covers AWS CloudWatch Logs and GCP Cloud Logging.

AWS calls the container "log group"; GCP calls it a "logger" (or a "sink" if you're exporting). Cloudjack exposes both through `create_log_group` / `delete_log_group` / `list_log_groups`.

## Log group lifecycle

=== "AWS"

    ```python
    from cloudjack import universal_factory

    log = universal_factory("logging", "aws", {"region_name": "us-east-1"})

    log.create_log_group("/app/prod/requests", retention_days=30)
    log.list_log_groups(prefix="/app/")
    log.delete_log_group("/app/prod/requests")
    ```

=== "GCP"

    ```python
    from cloudjack import universal_factory

    log = universal_factory("logging", "gcp", {"project_id": "my-project"})

    # Loggers auto-create on first write; create_log_group is a no-op
    # unless a sink destination is given.
    log.create_log_group("app-prod-requests", destination="bigquery.googleapis.com/projects/my-project/datasets/logs_ds")

    log.list_log_groups(prefix="app-")
    log.delete_log_group("app-prod-requests")
    ```

## Write log entries

```python
log.write_log("/app/prod/requests", "user signed in", severity="INFO")
log.write_log("/app/prod/requests", "db connection refused", severity="ERROR")
```

Valid severity values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. GCP additionally supports structured labels:

```python
log.write_log(
    "app-prod-requests",
    "user signed in",
    severity="INFO",
    labels={"user_id": "u-123", "env": "prod"},
)
```

## Read log entries

```python
# Latest 100
entries = log.read_logs("/app/prod/requests", limit=100)

for e in entries:
    print(e["timestamp"], e["severity"], e["message"])
```

### Filter pattern

```python
# AWS: CloudWatch Logs filter pattern
errors = log.read_logs("/app/prod/requests", limit=50, filter_pattern="ERROR")

# GCP: Cloud Logging advanced filter
errors = log.read_logs("app-prod-requests", limit=50, filter_pattern='severity="ERROR"')
```

### Time window (AWS only)

```python
import time

now_ms = int(time.time() * 1000)
hour_ago = now_ms - 3600 * 1000
recent = log.read_logs(
    "/app/prod/requests",
    limit=500,
    start_time=hour_ago,
    end_time=now_ms,
)
```

## Structured application logging

Cloudjack's Logging service is for writing to the **cloud** logging backend — use it from the edge of your app, not on every hot-path call. For local structured logs that also include request metadata, wrap `write_log` behind a helper:

```python
def app_log(log, message: str, **context) -> None:
    formatted = f"{message} | " + " ".join(f"{k}={v}" for k, v in context.items())
    log.write_log("/app/prod/requests", formatted, severity="INFO")

app_log(log, "request handled", path="/users", status=200, ms=42)
```

## Bulk write (async)

Fire many log writes concurrently without blocking the event loop:

```python
import asyncio

async def write_many(log, group: str, messages: list[str]) -> None:
    await asyncio.gather(*(
        log.awrite_log(group, m, severity="INFO") for m in messages
    ))

asyncio.run(write_many(log, "/app/prod/requests", ["a", "b", "c"]))
```

## Idempotent create

```python
from cloudjack import LogGroupAlreadyExistsError

try:
    log.create_log_group("/app/prod/requests", retention_days=30)
except LogGroupAlreadyExistsError:
    pass
```

## Error handling

```python
from cloudjack import LogGroupNotFoundError, LoggingError

try:
    log.read_logs("missing-group")
except LogGroupNotFoundError:
    ...
except LoggingError:
    ...
```

## CLI

```bash
cloudjack -p aws -s logging list-log-groups
cloudjack -p aws -s logging write-log /app/prod/requests "hello"
cloudjack -p aws -s logging read-logs /app/prod/requests -k '{"limit":10}'
```
