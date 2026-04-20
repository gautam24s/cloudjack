# Retry — Examples

`cloudjack.base.retry.retry` is a decorator that re-runs a callable with exponential backoff on a configurable set of exceptions.

## Signature

```python
from cloudjack.base.retry import retry

@retry(
    max_attempts=3,               # total attempts, including the first
    base_delay=1.0,               # initial delay (seconds)
    max_delay=30.0,               # cap per sleep
    backoff_factor=2.0,           # multiplier after each failure
    retryable_exceptions=None,    # defaults to (ConnectionError, TimeoutError, OSError)
)
def fetch():
    ...
```

## Default: network errors

With no arguments, the decorator retries on `ConnectionError`, `TimeoutError`, and `OSError`:

```python
from cloudjack.base.retry import retry
from cloudjack import universal_factory

storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

@retry()
def safe_list():
    return storage.list_buckets()
```

## Retry on provider errors

Point the decorator at Cloudjack's exception hierarchy to retry API failures:

```python
from cloudjack.base.retry import retry
from cloudjack import QueueError

@retry(max_attempts=5, retryable_exceptions=(QueueError,))
def send(queue, queue_id: str, body: str) -> str:
    return queue.send_message(queue_id, body)
```

Don't include `QueueAlreadyExistsError` or `QueueNotFoundError` in your retry set — those are deterministic and won't change between attempts.

## Retry with a narrower target

```python
from cloudjack import MessageError   # transient, network-related
from cloudjack.base.retry import retry

@retry(max_attempts=5, retryable_exceptions=(MessageError, ConnectionError))
def publish(queue, queue_id, body):
    return queue.send_message(queue_id, body)
```

## Backoff tuning

```python
# Aggressive retries for a flaky dependency
@retry(max_attempts=10, base_delay=0.2, max_delay=5.0, backoff_factor=1.5)
def fast_retry():
    ...

# Slow, patient retries for an external queue
@retry(max_attempts=6, base_delay=5.0, max_delay=60.0, backoff_factor=2.0)
def slow_retry():
    ...
```

Delays cap at `max_delay`, so `backoff_factor=2.0` with `base_delay=1.0` and `max_delay=30.0` produces: 1, 2, 4, 8, 16, 30, 30, 30, …

## In a worker loop

```python
from cloudjack import universal_factory
from cloudjack.base.retry import retry
from cloudjack import MessageError

q = universal_factory("queue", "aws", {"region_name": "us-east-1"})
QUEUE_ID = q.create_queue("jobs")

@retry(max_attempts=3, retryable_exceptions=(MessageError,))
def receive():
    return q.receive_messages(QUEUE_ID, max_messages=10, wait_time_seconds=20)

@retry(max_attempts=3, retryable_exceptions=(MessageError,))
def ack(handle: str):
    q.delete_message(QUEUE_ID, handle)

while True:
    for m in receive():
        try:
            process(m["body"])
        except Exception:
            continue
        ack(m["receipt_handle"])
```

## Wrapping an async call

The decorator targets sync callables. For async code, compose the retry loop manually with `asyncio.sleep`:

```python
import asyncio
from cloudjack import MessageError

async def asend_with_retry(q, queue_id, body, *, max_attempts=5, base_delay=1.0, backoff=2.0):
    delay = base_delay
    for attempt in range(max_attempts):
        try:
            return await q.asend_message(queue_id, body)
        except MessageError:
            if attempt + 1 == max_attempts:
                raise
            await asyncio.sleep(delay)
            delay *= backoff
```

## Logging

Retries emit `WARNING` logs via the `cloudjack` logger on each failed attempt, and `ERROR` on final exhaustion. Configure the logger to capture them:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("cloudjack").setLevel(logging.INFO)
```

## What the decorator does NOT do

- It doesn't jitter between retries — concurrent callers backing off together will thunder. For high-traffic callers, wrap the decorator call or use a jittered sleep.
- It doesn't restart long-running generators or streams — it retries the full function call from the top.
- It doesn't consume exceptions it can't retry — any non-matching exception propagates immediately.
