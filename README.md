# Cloudjack

[![PyPI](https://img.shields.io/pypi/v/cloudjack)](https://pypi.org/project/cloudjack/)
[![Python](https://img.shields.io/pypi/pyversions/cloudjack)](https://pypi.org/project/cloudjack/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A unified Python SDK for AWS and GCP. One factory, seven services, the same interface across providers.

## Features

- **Universal factory** — `universal_factory(service, provider, config)` returns a typed client for any supported service/provider pair.
- **7 services** — Compute, DNS, IAM, Logging, Queue, Secret Manager, Storage — each with AWS and GCP implementations.
- **Provider-agnostic** — swap `"aws"` ↔ `"gcp"` without changing call sites.
- **Typed returns** — `@overload` signatures give IDEs precise hover/autocomplete for each service.
- **Async support** — every service method has an auto-generated `a<method>` coroutine variant that runs the sync call in a thread.
- **Config flexibility** — pass a raw `dict` or a pre-built `AWSConfig` / `GCPConfig` model; missing fields resolve from environment variables or the SDK's default credential chain.
- **Connection pooling** — `ClientCache` shares one instance per `(provider, service, config)` key.
- **Retry policy** — `@retry(...)` decorator with exponential backoff.
- **Structured logging** — JSON logger for production log pipelines.
- **CLI** — `cloudjack --provider aws --service storage list-buckets`.

## Supported Services

| Service | AWS | GCP |
|---|---|---|
| Compute | EC2 | Compute Engine |
| DNS | Route 53 | Cloud DNS |
| IAM | IAM | IAM Admin |
| Logging | CloudWatch Logs | Cloud Logging |
| Queue | SQS | Pub/Sub |
| Secret Manager | Secrets Manager | Secret Manager |
| Storage | S3 | Cloud Storage |

## Installation

Requires **Python >= 3.10** (tested through 3.14).

```bash
pip install cloudjack[aws]     # AWS SDK (boto3)
pip install cloudjack[gcp]     # GCP SDKs (google-cloud-*)
pip install cloudjack[all]     # both
```

For development:

```bash
git clone https://github.com/gautam24s/cloudjack.git
cd cloudjack
uv sync --dev
```

## Quick Start

```python
from cloudjack import universal_factory

storage = universal_factory(
    service_name="storage",        # secret_manager | storage | queue | compute | dns | iam | logging
    cloud_provider="aws",          # aws | gcp
    config={
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "region_name": "us-east-1",
    },
)

storage.create_bucket("my-bucket")
storage.upload_object_from_file("my-bucket", "key", "/local/path")
```

## Config: dict or model

As of 0.3.0, `universal_factory` accepts a pre-built Pydantic model in addition to a raw dict. Useful when you build config once and pass it around.

```python
from cloudjack import universal_factory, AWSConfig

cfg = AWSConfig(
    aws_access_key_id="...",
    aws_secret_access_key="...",
    region_name="us-east-1",
)

storage = universal_factory("storage", "aws", cfg)
queue   = universal_factory("queue",   "aws", cfg)   # shares the cached client
```

Passing a `GCPConfig` where `cloud_provider="aws"` (or vice versa) raises `TypeError` at call time.

If you omit fields, Cloudjack resolves them from environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`) or falls back to the provider SDK's credential chain (EC2 IMDS, Application Default Credentials, etc.).

## Usage Examples

### Secret Manager

```python
sm = universal_factory("secret_manager", "aws", {"region_name": "ap-south-1"})

sm.create_secret("db-password", "s3cr3t")
value = sm.get_secret("db-password")
sm.update_secret("db-password", "rotated-value")
sm.delete_secret("db-password")
```

### Storage

```python
storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

# Buckets
storage.create_bucket("my-bucket")
storage.list_buckets()
storage.delete_bucket("my-bucket")

# Objects
storage.upload_object_from_file("my-bucket", "data.csv", "/local/data.csv")
storage.upload_object_from_bytes("my-bucket", "blob.bin", b"\x00\x01\x02")
storage.download_file("my-bucket", "data.csv", "/local/copy.csv")
content = storage.get_object("my-bucket", "data.csv")
storage.list_objects("my-bucket", prefix="data/")
storage.delete_object("my-bucket", "data.csv")

# Pre-signed URL
url = storage.generate_signed_url("my-bucket", "data.csv", expiration=3600)
```

### Compute

```python
compute = universal_factory("compute", "aws", {"region_name": "us-east-1"})

compute.list_instances()
compute.start_instance("i-0123456789abcdef0")
compute.stop_instance("i-0123456789abcdef0")
compute.terminate_instance("i-0123456789abcdef0")
```

### Queue / Messaging

```python
queue = universal_factory("queue", "aws", {"region_name": "us-east-1"})

url = queue.create_queue("tasks")
queue.send_message(url, "Hello, world!")
messages = queue.receive_messages(url)
queue.delete_queue(url)
```

### Async

Every sync method has an auto-generated `a<method>` async variant that runs on a worker thread. No separate async SDK is required.

```python
import asyncio
from cloudjack import universal_factory

async def main():
    storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})
    buckets = await storage.alist_buckets()
    await storage.aupload_object_from_file("my-bucket", "hello", "/tmp/hello.txt")

asyncio.run(main())
```

### Switching Providers

Change the provider string and the config; the rest of your code stays identical.

```python
# AWS
aws_storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

# GCP — same methods, different provider
gcp_storage = universal_factory("storage", "gcp", {"project_id": "my-gcp-project"})

aws_storage.list_buckets()
gcp_storage.list_buckets()
```

### Exceptions

Cloudjack wraps provider SDK errors in a shared hierarchy so you catch the same types regardless of provider.

```python
from cloudjack import BucketNotFoundError, StorageError

try:
    storage.delete_bucket("missing")
except BucketNotFoundError:
    print("Bucket does not exist")
except StorageError as e:
    print(f"Storage error: {e}")
```

## CLI

```bash
cloudjack -p aws -s storage list-buckets
cloudjack -p aws -s secret_manager create-secret my-secret s3cr3t
cloudjack -p gcp -s secret_manager get-secret -c '{"project_id":"my-project"}' my-secret
```

Operation names map dash-separated → underscored method names (`list-buckets` → `list_buckets`). The CLI enforces an allowlist derived from the service interface so arbitrary attributes can't be called.

## Project Structure

```
cloudjack/
├── pyproject.toml
├── cloudjack/
│   ├── __init__.py
│   ├── cli.py
│   ├── factory.py              # universal_factory + provider registry
│   ├── base/                   # service interfaces and shared utilities
│   │   ├── compute.py          # ComputeService (ABC)
│   │   ├── dns.py              # DNSService (ABC)
│   │   ├── iam.py              # IAMService (ABC)
│   │   ├── logging_service.py  # LoggingService (ABC)
│   │   ├── queue.py            # QueueService (ABC)
│   │   ├── secret_manager.py   # SecretManagerService (ABC)
│   │   ├── storage.py          # StorageService (ABC)
│   │   ├── async_support.py    # AsyncMixin
│   │   ├── client_cache.py     # singleton client cache
│   │   ├── config.py           # Pydantic config models
│   │   ├── exceptions.py       # exception hierarchy
│   │   ├── logger.py           # structured JSON logger
│   │   ├── retry.py            # @retry decorator
│   │   └── types.py            # return-shape TypedDicts
│   ├── aws/                    # AWS implementations
│   └── gcp/                    # GCP implementations
├── tests/                      # test suite (uv run pytest)
└── docs/                       # MkDocs documentation
```

## Extending

**Add a service** — add an ABC in `cloudjack/base/<service>.py`, exceptions in `cloudjack/base/exceptions.py`, implementations in `cloudjack/aws/<service>.py` and `cloudjack/gcp/<service>.py`, register the class in each provider's `SERVICE_REGISTRY`, and add an `@overload` in `cloudjack/factory.py`.

**Add a provider** — create `cloudjack/<provider>/` with a `factory.py` exporting `SERVICE_REGISTRY`, register it in `_PROVIDER_MODULES` in `cloudjack/factory.py`, add a matching Pydantic model in `cloudjack/base/config.py`, and extend the `existing_cloud_providers` literal.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.

## Exception Reference

| Exception | Description |
|---|---|
| `CloudjackError` | Root of the exception hierarchy |
| `SecretManagerError` / `SecretNotFoundError` / `SecretAlreadyExistsError` | Secret manager operations |
| `StorageError` / `BucketNotFoundError` / `BucketAlreadyExistsError` / `ObjectNotFoundError` | Storage operations |
| `QueueError` / `QueueNotFoundError` / `QueueAlreadyExistsError` / `MessageError` | Queue / messaging operations |
| `ComputeError` / `InstanceNotFoundError` / `InstanceAlreadyExistsError` | Compute operations |
| `DNSError` / `ZoneNotFoundError` / `ZoneAlreadyExistsError` / `RecordNotFoundError` | DNS operations |
| `IAMError` / `RoleNotFoundError` / `RoleAlreadyExistsError` / `PolicyNotFoundError` | IAM operations |
| `LoggingError` / `LogGroupNotFoundError` / `LogGroupAlreadyExistsError` | Logging operations |

## Roadmap

- [ ] **Azure support** — concrete implementations behind the existing interfaces.
- [ ] **DigitalOcean Spaces** — S3-compatible, thin adapter.
- [ ] **Integration tests** against LocalStack (AWS) and the GCP emulator.

### Recently shipped

- **0.3.0** — `*Blueprint` → `*Service` rename; `universal_factory` accepts `AWSConfig` / `GCPConfig` instances directly.
- **0.2.0** — security and correctness audit: removed leaked credentials, narrowed GCP exception handling, etag retry on GCP IAM policy updates, symmetric `delete_queue`, hardened `ClientCache` locking, CLI allowlist, factory cache-key fix, hid interface ABCs from the public package namespace.
- **0.1.x** — initial multi-cloud factory, AWS + GCP implementations for all 7 services, async mixin, Pydantic config, CLI, PyPI release.

## License

MIT
