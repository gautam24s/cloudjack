# Getting Started

## Installation

Requires **Python >= 3.10**.

```bash
pip install cloudjack[all]
```

Or install a single provider:

```bash
pip install cloudjack[aws]
pip install cloudjack[gcp]
```

## Creating a Service Client

Every service is created through [`universal_factory`][cloudjack.factory.universal_factory]:

```python
from cloudjack import universal_factory

client = universal_factory(
    service_name="storage",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)
```

The factory is overloaded per `service_name` so your IDE autocompletes methods precisely (e.g. `StorageService` for `"storage"`, `QueueService` for `"queue"`).

## Configuration

`config` accepts either a raw `dict` or a pre-built [`AWSConfig`][cloudjack.base.config.AWSConfig] / [`GCPConfig`][cloudjack.base.config.GCPConfig] instance. Missing fields resolve automatically from environment variables, and anything still missing falls through to the provider SDK's default credential chain (EC2 IMDS, `~/.aws/credentials`, GCP ADC, etc.).

=== "Dict"

    ```python
    storage = universal_factory("storage", "aws", {
        "aws_access_key_id": "AKIA...",
        "aws_secret_access_key": "...",
        "region_name": "us-east-1",
    })
    ```

=== "Config model"

    ```python
    from cloudjack import AWSConfig, universal_factory

    cfg = AWSConfig(
        aws_access_key_id="AKIA...",
        aws_secret_access_key="...",
        region_name="us-east-1",
    )
    storage = universal_factory("storage", "aws", cfg)
    queue   = universal_factory("queue",   "aws", cfg)
    ```

=== "Environment variables"

    ```bash
    export AWS_ACCESS_KEY_ID="AKIA..."
    export AWS_SECRET_ACCESS_KEY="..."
    export AWS_DEFAULT_REGION="us-east-1"
    ```

    ```python
    storage = universal_factory("storage", "aws")
    ```

Passing a `GCPConfig` with `cloud_provider="aws"` (or vice versa) raises `TypeError` at call time. See [Config](api/core/config.md) for the full model reference.

## Available Services

Pass these as `service_name`:

| `service_name` | Return type | Description |
|---|---|---|
| `"secret_manager"` | [`SecretManagerService`][cloudjack.base.secret_manager.SecretManagerService] | CRUD for secrets |
| `"storage"` | [`StorageService`][cloudjack.base.storage.StorageService] | Buckets and objects |
| `"queue"` | [`QueueService`][cloudjack.base.queue.QueueService] | Messaging queues |
| `"compute"` | [`ComputeService`][cloudjack.base.compute.ComputeService] | VM lifecycle |
| `"dns"` | [`DNSService`][cloudjack.base.dns.DNSService] | DNS zones and records |
| `"iam"` | [`IAMService`][cloudjack.base.iam.IAMService] | Roles and policies |
| `"logging"` | [`LoggingService`][cloudjack.base.logging_service.LoggingService] | Log groups and entries |

## Async

Every sync method has an auto-generated `a<method>` coroutine variant (via `AsyncMixin`) that runs the underlying call in a thread. No separate async SDK is required.

```python
import asyncio
from cloudjack import universal_factory

async def main():
    storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})
    buckets = await storage.alist_buckets()
    await storage.aupload_object_from_file("my-bucket", "hello", "/tmp/hello.txt")

asyncio.run(main())
```

## Error Handling

Provider SDK errors are wrapped in a provider-agnostic hierarchy rooted at [`CloudjackError`][cloudjack.base.exceptions.CloudjackError]:

```python
from cloudjack import BucketNotFoundError, StorageError

try:
    storage.delete_bucket("missing")
except BucketNotFoundError:
    ...
except StorageError as e:
    ...
```

## Next Steps

- [Universal Factory API](api/factory.md)
- [Service Interfaces](api/services/storage.md)
- [AWS Implementations](api/aws/storage.md) / [GCP Implementations](api/gcp/storage.md)
- [Migration guide](migration.md) — replacing direct boto3 / google-cloud calls.
- [CLI](cli.md)
