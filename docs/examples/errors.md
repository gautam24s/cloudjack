# Error Handling — Examples

Cloudjack wraps SDK errors in a provider-agnostic hierarchy rooted at `CloudjackError`. You catch the same types whether you're on AWS or GCP.

## The hierarchy

```
CloudjackError
├── SecretManagerError
│   ├── SecretNotFoundError
│   └── SecretAlreadyExistsError
├── StorageError
│   ├── BucketNotFoundError
│   ├── BucketAlreadyExistsError
│   └── ObjectNotFoundError
├── QueueError
│   ├── QueueNotFoundError
│   ├── QueueAlreadyExistsError
│   └── MessageError
├── ComputeError
│   ├── InstanceNotFoundError
│   └── InstanceAlreadyExistsError
├── DNSError
│   ├── ZoneNotFoundError
│   ├── ZoneAlreadyExistsError
│   └── RecordNotFoundError
├── IAMError
│   ├── RoleNotFoundError
│   ├── RoleAlreadyExistsError
│   └── PolicyNotFoundError
└── LoggingError
    ├── LogGroupNotFoundError
    └── LogGroupAlreadyExistsError
```

Every exception is re-exported from the top-level `cloudjack` package.

## Basic catch-and-branch

```python
from cloudjack import universal_factory, BucketNotFoundError, ObjectNotFoundError, StorageError

storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

try:
    blob = storage.get_object("my-bucket", "file.txt")
except BucketNotFoundError:
    # Bucket is gone
    ...
except ObjectNotFoundError:
    # Bucket exists, object doesn't
    ...
except StorageError as e:
    # Any other storage API failure
    ...
```

## Make a call idempotent

```python
from cloudjack import BucketAlreadyExistsError, BucketNotFoundError

def ensure_bucket(storage, name: str) -> None:
    try:
        storage.create_bucket(name)
    except BucketAlreadyExistsError:
        pass

def ensure_no_bucket(storage, name: str) -> None:
    try:
        storage.delete_bucket(name)
    except BucketNotFoundError:
        pass
```

## Reacting differently per error subtype

```python
from cloudjack import SecretNotFoundError, SecretAlreadyExistsError

def upsert(sm, name: str, value: str) -> None:
    try:
        sm.update_secret(name, value)
    except SecretNotFoundError:
        try:
            sm.create_secret(name, value)
        except SecretAlreadyExistsError:
            # concurrent writer got there first
            sm.update_secret(name, value)
```

## Catch-all for unexpected SDK failures

Catching the service root (`StorageError`, `QueueError`, …) gives you everything **that came from the provider SDK**. Programming errors, bad arguments, and unrelated Python exceptions propagate untouched — which is what you want.

```python
from cloudjack import StorageError

try:
    storage.upload_file("my-bucket", "key", "/local/file")
except StorageError as e:
    # Retry, alert, or fall through — you got here because the provider
    # returned an error, not because your code is broken.
    logger.error("upload failed: %s", e)
    raise
```

## Catch every Cloudjack error

```python
from cloudjack import CloudjackError

try:
    ...
except CloudjackError:
    # anything that originated inside Cloudjack — storage, queue, dns, etc.
    ...
```

## Chained exceptions

Every wrapped SDK error preserves the original via `__cause__`:

```python
try:
    storage.delete_bucket("ghost")
except BucketNotFoundError as e:
    print(e)              # 'Bucket ghost not found'
    print(e.__cause__)    # botocore.exceptions.ClientError(...)
```

Use `e.__cause__` when you need the underlying provider error code for logging or rare provider-specific branching.

## Pairing with retry

The retry decorator is orthogonal to the exception hierarchy — it only retries on the exceptions you tell it to:

```python
from cloudjack.base.retry import retry
from cloudjack import QueueError

@retry(max_attempts=5, retryable_exceptions=(QueueError,))
def send(queue, queue_id: str, body: str) -> str:
    return queue.send_message(queue_id, body)
```

See [Retry examples](retry.md) for more patterns.
