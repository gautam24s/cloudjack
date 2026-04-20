# Async — Examples

Every service method has an auto-generated `a<method>` coroutine variant that runs the underlying sync call in a worker thread via `asyncio.to_thread`. You don't install a separate async SDK — the existing sync implementation is reused under the hood, so behaviour is identical apart from the event-loop integration.

## The pattern

```python
import asyncio
from cloudjack import universal_factory

storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

async def main():
    buckets = await storage.alist_buckets()
    await storage.aupload_file("my-bucket", "hello", "/tmp/hello.txt")
    blob = await storage.aget_object("my-bucket", "hello")
    return blob

asyncio.run(main())
```

For every sync method `foo`, the mixin adds `afoo` with the same parameters.

## Concurrent fan-out

`asyncio.gather` lets you run many calls in parallel. Each one occupies a worker thread, so N calls run in roughly the time of the slowest one:

```python
import asyncio
from cloudjack import universal_factory

sm = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})

async def load_secrets(names: list[str]) -> dict[str, str]:
    values = await asyncio.gather(*(sm.aget_secret(n) for n in names))
    return dict(zip(names, values))

asyncio.run(load_secrets(["db/password", "redis/password", "api-key"]))
```

## Concurrent cross-provider

Query AWS and GCP at the same time:

```python
import asyncio
from cloudjack import universal_factory

aws = universal_factory("storage", "aws", {"region_name": "us-east-1"})
gcp = universal_factory("storage", "gcp", {"project_id": "my-project"})

async def snapshot_buckets():
    aws_buckets, gcp_buckets = await asyncio.gather(
        aws.alist_buckets(),
        gcp.alist_buckets(),
    )
    return {"aws": aws_buckets, "gcp": gcp_buckets}

asyncio.run(snapshot_buckets())
```

## Rate-limited fan-out

For large fan-outs, cap concurrency with a semaphore to avoid overwhelming the provider or hitting API limits:

```python
import asyncio
from pathlib import Path

async def upload_many(storage, bucket: str, files: list[Path], concurrency: int = 10):
    sem = asyncio.Semaphore(concurrency)

    async def one(f: Path):
        async with sem:
            await storage.aupload_file(bucket, f.name, str(f))

    await asyncio.gather(*(one(f) for f in files))
```

## Long-poll queue worker

```python
import asyncio

async def worker(q, queue_id):
    while True:
        msgs = await q.areceive_messages(queue_id, max_messages=10, wait_time_seconds=20)
        for m in msgs:
            # handle concurrently within the batch
            asyncio.create_task(handle_and_ack(q, queue_id, m))

async def handle_and_ack(q, queue_id, msg):
    try:
        await process(msg["body"])
    except Exception:
        return  # don't ack → visibility timeout will return it
    await q.adelete_message(queue_id, msg["receipt_handle"])
```

## Gotchas

- **It's thread-based, not true async I/O.** The coroutine hands the sync call off to `asyncio.to_thread`. A few thousand concurrent calls is fine; hundreds of thousands isn't — at that scale, use the provider's native async SDK directly.
- **The sync methods are thread-safe for reads.** Instances are cached per `(provider, service, config)`, so every coroutine shares the same underlying client. The cloud SDKs (`boto3`, `google-cloud-*`) are generally thread-safe for calls, but keep long-running mutations (e.g. the GCP IAM policy binding flow) aware of that — Cloudjack already wraps the IAM read-modify-write in an etag retry loop for you.
- **Exceptions propagate as-is.** A sync call that raises `BucketNotFoundError` raises the same exception when awaited via `abucket_not_found`.

## Mixing sync and async

You can call sync and async variants against the same service instance in the same program. `ClientCache` returns the same object in both paths:

```python
storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

def sync_path():
    return storage.list_buckets()

async def async_path():
    return await storage.alist_buckets()
```
