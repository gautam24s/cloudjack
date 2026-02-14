# Getting Started

## Installation

```bash
pip install cloudjack[all]
```

Or install per-provider:

```bash
pip install cloudjack[aws]
pip install cloudjack[gcp]
```

## Creating a Service Client

All services are created through [`universal_factory`][cloud.factory.universal_factory]:

```python
from cloud import universal_factory

client = universal_factory(
    service_name="storage",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)
```

The factory returns a typed instance — your IDE will autocomplete methods based on the `service_name` you pass.

## Configuration

Credentials can be passed explicitly or resolved from environment variables automatically:

=== "Explicit"

    ```python
    storage = universal_factory("storage", "aws", {
        "aws_access_key_id": "AKIA...",
        "aws_secret_access_key": "...",
        "region_name": "us-east-1",
    })
    ```

=== "Environment Variables"

    ```bash
    export AWS_ACCESS_KEY_ID="AKIA..."
    export AWS_SECRET_ACCESS_KEY="..."
    export AWS_DEFAULT_REGION="us-east-1"
    ```

    ```python
    storage = universal_factory("storage", "aws", {})
    ```

See [Config](api/core/config.md) for full details on `AWSConfig` and `GCPConfig`.

## Available Services

Pass these as `service_name`:

| `service_name` | Blueprint | Description |
|---|---|---|
| `"secret_manager"` | [`SecretManagerBlueprint`][cloud.base.secret_manager.SecretManagerBlueprint] | CRUD for secrets |
| `"storage"` | [`CloudStorageBlueprint`][cloud.base.storage.CloudStorageBlueprint] | Buckets and objects |
| `"queue"` | [`QueueBlueprint`][cloud.base.queue.QueueBlueprint] | Messaging queues |
| `"compute"` | [`ComputeBlueprint`][cloud.base.compute.ComputeBlueprint] | VM lifecycle |
| `"dns"` | [`DNSBlueprint`][cloud.base.dns.DNSBlueprint] | DNS zones and records |
| `"iam"` | [`IAMBlueprint`][cloud.base.iam.IAMBlueprint] | Roles and policies |
| `"logging"` | [`LoggingBlueprint`][cloud.base.logging_service.LoggingBlueprint] | Log groups and entries |
