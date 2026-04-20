# Cloudjack

[![PyPI](https://img.shields.io/pypi/v/cloudjack)](https://pypi.org/project/cloudjack/)
[![Python](https://img.shields.io/pypi/pyversions/cloudjack)](https://pypi.org/project/cloudjack/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A unified Python SDK for interacting with cloud services across multiple providers (AWS, GCP) through a single, consistent interface.

## Features

- **Universal Factory** — One function to create any cloud service client, regardless of provider.
- **7 Services** — Compute, DNS, IAM, Logging, Queue, Secret Manager, and Storage — each with AWS and GCP implementations.
- **Provider-agnostic interfaces** — Swap cloud providers without changing your application code.
- **Async support** — Async variants of all service methods via `asyncio.to_thread`.
- **Connection pooling** — Singleton `ClientCache` reuses clients per provider+config.
- **Retry policies** — Configurable retry/backoff decorator.
- **Config validation** — Pydantic models with automatic credential resolution from env vars.
- **CLI tool** — `cloudjack --provider aws --service storage list-buckets`.
- **Typed returns** — `@overload` annotations give your IDE full autocomplete on returned service objects.

## Supported Services

| Service | AWS | GCP |
|---------|-----|-----|
| Compute | EC2 | Compute Engine |
| DNS | Route 53 | Cloud DNS |
| IAM | IAM | IAM |
| Logging | CloudWatch Logs | Cloud Logging |
| Queue | SQS | Pub/Sub |
| Secrets | Secrets Manager | Secret Manager |
| Storage | S3 | Cloud Storage |

## Installation

Requires **Python >= 3.10**.

```bash
pip install cloudjack          # core only
pip install cloudjack[aws]     # with AWS dependencies (boto3)
pip install cloudjack[gcp]     # with GCP dependencies (google-cloud-*)
pip install cloudjack[all]     # everything
```

For development:

```bash
git clone https://github.com/gautam24s/cloudjack.git
cd cloudjack
uv sync
```

## Quick Start

```python
from cloud import universal_factory

# Create any service client with one function
client = universal_factory(
    service_name="storage",       # or: compute, dns, iam, logging, queue, secret_manager
    cloud_provider="aws",         # or: gcp
    config={
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "region_name": "us-east-1",
    },
)
```

## Usage Examples

### Secret Manager

```python
client = universal_factory(
    service_name="secret_manager",
    cloud_provider="aws",
    config={"region_name": "ap-south-1"},
)

secret = client.get_secret("my_secret")
client.create_secret("new_secret", "s3cr3t_value")
client.update_secret("new_secret", "updated_value")
client.delete_secret("new_secret")
```

### Cloud Storage

```python
storage = universal_factory(
    service_name="storage",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)

# Buckets
storage.create_bucket("my-bucket")
buckets = storage.list_buckets()
storage.delete_bucket("my-bucket")

# Objects
storage.upload_file("my-bucket", "data.csv", "/local/data.csv")
storage.download_file("my-bucket", "data.csv", "/local/copy.csv")
content = storage.get_object("my-bucket", "data.csv")
keys = storage.list_objects("my-bucket", prefix="data/")
storage.delete_object("my-bucket", "data.csv")

# Pre-signed URLs
url = storage.generate_signed_url("my-bucket", "data.csv", expiration=3600)
```

### Compute

```python
compute = universal_factory(
    service_name="compute",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)

instances = compute.list_instances()
compute.start_instance("i-0123456789abcdef0")
compute.stop_instance("i-0123456789abcdef0")
compute.terminate_instance("i-0123456789abcdef0")
```

### Queue / Messaging

```python
queue = universal_factory(
    service_name="queue",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)

queue.create_queue("my-queue")
queue.send_message("my-queue", "Hello, world!")
messages = queue.receive_messages("my-queue")
queue.delete_queue("my-queue")
```

### Switching Providers

The same interface works across providers — just change `cloud_provider`:

```python
# AWS
aws_storage = universal_factory(
    service_name="storage",
    cloud_provider="aws",
    config={"region_name": "us-east-1"},
)

# GCP — same methods, different provider
gcp_storage = universal_factory(
    service_name="storage",
    cloud_provider="gcp",
    config={"project_id": "my-gcp-project"},
)

# Both have the same interface
aws_storage.list_buckets()
gcp_storage.list_buckets()
```

## Codebase Review Findings

During a recent codebase review, the following issues were identified and successfully resolved:

### 1. Logical Bugs
- **Client Caching ignored:** The `universal_factory` function was instantiating new service clients (e.g., `boto3.client` or GCP abstractions) on every call instead of utilizing the `ClientCache` singleton. This circumvented the intended connection pooling behavior. It has been fixed to properly cache and reuse clients based on the provider and configuration.

### 2. Typing Issues
- **Mypy Return Type Violations:** In `cloud/gcp/iam.py` and `cloud/gcp/secret_manager.py`, functions declared to return `str` were implicitly returning `Any` due to dynamic properties on the GCP response objects. These have been cast to strings to ensure type-safety.

### 3. Syntax & Style Issues
- **Unused Imports (Ruff/Flake8):** Several unused imports were found and removed across the Cloud directory (such as `PolicyNotFoundError` in AWS IAM and `PubsubMessage` in GCP Queue).

*Note: Following extensive bisection on testing anomalies, it was confirmed that tests run stably both locally and in CI.*

## Project Structure

```
cloudjack/
├── main.py
├── pyproject.toml
├── cloud/
│   ├── __init__.py
│   ├── cli.py
│   ├── factory.py              # Universal factory with provider registry
│   ├── base/                   # Abstract blueprints and core utilities
│   │   ├── compute.py          # ComputeService (ABC)
│   │   ├── dns.py              # DNSService (ABC)
│   │   ├── iam.py              # IAMService (ABC)
│   │   ├── logging_service.py  # LoggingService (ABC)
│   │   ├── queue.py            # QueueService (ABC)
│   │   ├── secret_manager.py   # SecretManagerService (ABC)
│   │   ├── storage.py          # StorageService (ABC)
│   │   ├── async_support.py    # AsyncMixin
│   │   ├── client_cache.py     # Singleton client cache
│   │   ├── config.py           # Pydantic config models
│   │   ├── exceptions.py       # Exception hierarchy
│   │   ├── logger.py           # Structured JSON logging
│   │   └── retry.py            # Retry/backoff decorator
│   ├── aws/                    # AWS implementations
│   └── gcp/                    # GCP implementations
├── tests/                      # Full test suite
└── docs/                       # MkDocs documentation
```

## Adding a New Cloud Provider

1. Create a directory under `cloud/<provider>/`.
2. Implement service classes inheriting from the base blueprints.
3. Create a `factory.py` with a `SERVICE_REGISTRY` dict mapping service names to classes.
4. Register it in `cloud/factory.py` under `_FACTORY_REGISTRY`.

## Exceptions

| Exception | Description |
|---|---|
| `CloudjackError` | Root exception for all Cloudjack errors |
| `SecretManagerError` | Base exception for secret manager operations |
| `SecretNotFoundError` | Secret does not exist |
| `SecretAlreadyExistsError` | Secret already exists |
| `StorageError` | Base exception for storage operations |
| `BucketNotFoundError` | Bucket does not exist |
| `BucketAlreadyExistsError` | Bucket already exists |
| `ObjectNotFoundError` | Object does not exist |
| `QueueError` | Base exception for queue operations |
| `QueueNotFoundError` | Queue or topic does not exist |
| `QueueAlreadyExistsError` | Queue or topic already exists |
| `MessageError` | Failed to send, receive, or delete a message |
| `ComputeError` | Base exception for compute operations |
| `InstanceNotFoundError` | VM instance not found |
| `InstanceAlreadyExistsError` | VM instance already exists |
| `DNSError` | Base exception for DNS operations |
| `ZoneNotFoundError` | DNS zone not found |
| `ZoneAlreadyExistsError` | DNS zone already exists |
| `RecordNotFoundError` | DNS record not found |
| `IAMError` | Base exception for IAM operations |
| `RoleNotFoundError` | IAM role not found |
| `RoleAlreadyExistsError` | IAM role already exists |
| `PolicyNotFoundError` | IAM policy not found |
| `LoggingError` | Base exception for logging operations |
| `LogGroupNotFoundError` | Log group or sink not found |
| `LogGroupAlreadyExistsError` | Log group or sink already exists |

## License

MIT

## Roadmap

### Providers

- [ ] **Azure support** — Implement Azure services behind the existing blueprints.
- [ ] **DigitalOcean Spaces** — S3-compatible, minimal adapter needed.

### Core Improvements

- [ ] **Integration tests** — Test against real cloud APIs (LocalStack for AWS, emulator for GCP) in CI.
- [ ] **GitHub Actions CI** — Automated lint, test, type-check on push/PR.

### Done

- [x] 7 service blueprints (Compute, DNS, IAM, Logging, Queue, Secret Manager, Storage)
- [x] AWS and GCP implementations for all services
- [x] Async support via `AsyncMixin`
- [x] Connection pooling via `ClientCache`
- [x] Retry policies with configurable backoff
- [x] Pydantic config validation with credential auto-resolution
- [x] Structured JSON logging
- [x] CLI tool
- [x] Published to PyPI with optional extras
- [x] Full test suite with coverage reporting
- [x] API documentation via MkDocs
- [x] Migration guide and contributing guide
