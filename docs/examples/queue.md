# Queue — Examples

Covers AWS SQS and GCP Pub/Sub. Cloudjack normalises the producer/consumer API so the same `send_message` / `receive_messages` / `delete_message` flow works on either.

Provider-specific terminology:

| Concept | AWS SQS | GCP Pub/Sub |
|---|---|---|
| Queue | SQS queue (URL) | Topic + pull subscription |
| Message ID | `MessageId` | `messageId` |
| Delete handle | `ReceiptHandle` | `ackId` |

`create_queue` returns a queue URL on AWS and a subscription path on GCP. Pass that value as `queue_id` to subsequent calls.

## Producer

```python
from cloudjack import universal_factory

q = universal_factory("queue", "aws", {"region_name": "us-east-1"})

queue_id = q.create_queue("tasks")
mid = q.send_message(queue_id, "hello world")

# With metadata attributes (both providers)
q.send_message(queue_id, "payload", message_attributes={"source": "web"})
```

## Consumer loop

```python
import time

def consume(queue, queue_id, handler):
    while True:
        msgs = queue.receive_messages(queue_id, max_messages=10, wait_time_seconds=20)
        if not msgs:
            continue
        for m in msgs:
            try:
                handler(m["body"])
            except Exception:
                # Leave un-acked so it becomes visible again after the visibility timeout
                continue
            else:
                queue.delete_message(queue_id, m["receipt_handle"])
```

For AWS, `wait_time_seconds` enables long-polling (up to 20s). For GCP, it's ignored — polling happens at the subscription's ack deadline.

## Fan-out worker (async)

Fetch a batch, process items concurrently, ack each one when its handler returns:

```python
import asyncio
from cloudjack import universal_factory

q = universal_factory("queue", "aws", {"region_name": "us-east-1"})
QUEUE_ID = q.create_queue("tasks")

async def handle(body: str) -> None:
    # ... your processing ...
    await asyncio.sleep(0.1)

async def worker():
    while True:
        msgs = await q.areceive_messages(QUEUE_ID, max_messages=10, wait_time_seconds=20)
        if not msgs:
            continue
        # Process concurrently, then ack successful ones
        results = await asyncio.gather(
            *(handle(m["body"]) for m in msgs),
            return_exceptions=True,
        )
        for m, res in zip(msgs, results):
            if not isinstance(res, Exception):
                await q.adelete_message(QUEUE_ID, m["receipt_handle"])

asyncio.run(worker())
```

## Delayed delivery (AWS)

```python
q.send_message(queue_id, "later", delay_seconds=60)
```

The `delay_seconds` keyword is ignored on GCP — use Cloud Tasks or a scheduled publisher if you need delivery delays there.

## Batch producer

Cloudjack doesn't yet expose a batch-send helper, but the async variant lets you send many messages concurrently:

```python
import asyncio

async def publish_batch(q, queue_id, bodies: list[str]) -> list[str]:
    return await asyncio.gather(*(q.asend_message(queue_id, b) for b in bodies))

ids = asyncio.run(publish_batch(q, QUEUE_ID, ["a", "b", "c"]))
```

## List queues

```python
# All queues
q.list_queues()

# Filter by prefix
q.list_queues(prefix="prod-")
```

## Idempotent queue creation

```python
from cloudjack import QueueAlreadyExistsError

try:
    q.create_queue("tasks")
except QueueAlreadyExistsError:
    pass
```

## Delete a queue (idempotent)

```python
from cloudjack import QueueNotFoundError

try:
    q.delete_queue("tasks")
except QueueNotFoundError:
    # already gone — treat as success
    pass
```

On GCP, `delete_queue` only raises `QueueNotFoundError` when **both** the topic and its subscription are already missing. If either component exists, it's deleted and the call succeeds (idempotent on partial state).

## CLI

```bash
cloudjack -p aws -s queue create-queue tasks
cloudjack -p aws -s queue send-message <queue-url> "hello"
cloudjack -p aws -s queue receive-messages <queue-url>
```
