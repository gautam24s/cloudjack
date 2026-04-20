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

| `service_name` | Return type | Description |
|---|---|---|
| `"secret_manager"` | [`SecretManagerService`][cloud.base.secret_manager.SecretManagerService] | CRUD for secrets |
| `"storage"` | [`StorageService`][cloud.base.storage.StorageService] | Buckets and objects |
| `"queue"` | [`QueueService`][cloud.base.queue.QueueService] | Messaging queues |
| `"compute"` | [`ComputeService`][cloud.base.compute.ComputeService] | VM lifecycle |
| `"dns"` | [`DNSService`][cloud.base.dns.DNSService] | DNS zones and records |
| `"iam"` | [`IAMService`][cloud.base.iam.IAMService] | Roles and policies |
| `"logging"` | [`LoggingService`][cloud.base.logging_service.LoggingService] | Log groups and entries |
