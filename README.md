# Cloudjack

A unified Python SDK for interacting with cloud services across multiple providers (AWS, GCP) through a single, consistent interface.

## Features

- **Universal Factory** — One function to create any cloud service client, regardless of provider.
- **Secret Manager** — CRUD operations for secrets (AWS Secrets Manager, GCP Secret Manager).
- **Cloud Storage** — CRUD operations for buckets and objects (AWS S3).
- **Provider-agnostic interfaces** — Swap cloud providers without changing your application code.
- **Typed returns** — `@overload` annotations give your IDE full autocomplete on returned service objects.

## Project Structure

```
cloudjack/
├── main.py                  # Entry point
├── pyproject.toml
├── cloud/
│   ├── __init__.py          # Exports universal_factory
│   ├── factory.py           # Universal factory with provider registry
│   ├── base/
│   │   ├── __init__.py
│   │   ├── secret_manager.py   # SecretManagerBlueprint (ABC)
│   │   ├── storage.py          # CloudStorageBlueprint (ABC)
│   │   └── exceptions.py       # Shared exception classes
│   ├── aws/
│   │   ├── __init__.py
│   │   ├── factory.py          # AWS service registry
│   │   ├── secret_manager.py   # AWS Secrets Manager implementation
│   │   └── storage.py          # AWS S3 implementation
│   └── gcp/
│       ├── __init__.py
│       ├── factory.py          # GCP service registry
│       └── secret_manager.py   # GCP Secret Manager implementation
```

## Installation

Requires Python >= 3.14.

```bash
uv sync
```

## Usage

### Secret Manager

```python
from cloud import universal_factory

# AWS
client = universal_factory(
    service_name="secret_manager",
    cloud_provider="aws",
    config={
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "region_name": "ap-south-1",
    },
)

secret = client.get_secret("my_secret")
client.create_secret("new_secret", "s3cr3t_value")
client.update_secret("new_secret", "updated_value")
client.delete_secret("new_secret")

# GCP — same interface, different provider
client = universal_factory(
    service_name="secret_manager",
    cloud_provider="gcp",
    config={...},
)
```

### Cloud Storage (AWS S3)

```python
from cloud import universal_factory

storage = universal_factory(
    service_name="storage",
    cloud_provider="aws",
    config={
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "region_name": "us-east-1",
    },
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

## Adding a New Cloud Provider

1. Create a directory under `cloud/<provider>/`.
2. Implement service classes inheriting from the base blueprints (`SecretManagerBlueprint`, `CloudStorageBlueprint`).
3. Create a `factory.py` with a `SERVICE_REGISTRY` dict mapping service names to classes.
4. Register it in `cloud/factory.py` under `_FACTORY_REGISTRY`.

## Exceptions

| Exception | Description |
|---|---|
| `SecretManagerError` | Base exception for secret manager operations |
| `SecretNotFoundError` | Secret does not exist |
| `SecretAlreadyExistsError` | Secret already exists |
| `StorageError` | Base exception for storage operations |
| `BucketNotFoundError` | Bucket does not exist |
| `BucketAlreadyExistsError` | Bucket already exists |
| `ObjectNotFoundError` | Object does not exist |

## License

MIT

## Roadmap

Proposals and future work to make Cloudjack a production-ready library.

### Providers

- [ ] **Azure support** — Implement Azure Blob Storage and Azure Key Vault behind the existing blueprints.
- [ ] **DigitalOcean Spaces** — S3-compatible, minimal adapter needed.

### New Service Blueprints

- [x] **Queue/Messaging** — Unified interface for AWS SQS, GCP Pub/Sub, Azure Service Bus.
- [x] **IAM/Auth** — Role and policy management across providers.
- [x] **DNS** — Route53, Cloud DNS, Azure DNS under one blueprint.
- [x] **Compute** — Basic VM lifecycle (create, start, stop, terminate).
- [x] **Logging** — CloudWatch Logs, Cloud Logging, Azure Monitor.

### Core Improvements

- [x] **Async support** — Async variants of all service methods via `asyncio.to_thread` + `AsyncMixin`.
- [x] **Connection pooling** — Singleton `ClientCache` reuses clients per provider+config.
- [x] **Retry policies** — Configurable retry/backoff decorator in `cloud.base.retry`.
- [x] **Config validation** — Pydantic models for provider configs (`AWSConfig`, `GCPConfig`).
- [x] **Credential chain** — Auto-resolve credentials from env vars via Pydantic `model_validator`.
- [x] **Logging & observability** — Structured JSON logging with request IDs in `cloud.base.logger`.

### Packaging & Distribution

- [ ] **Publish to PyPI** — Proper packaging with extras (`pip install cloudjack[aws]`, `cloudjack[gcp]`). Use `./publish.sh`.
- [x] **Optional dependencies** — Only install `boto3` if using AWS, `google-cloud-*` if using GCP.
- [x] **CLI tool** — `cloudjack --provider aws --service storage list-buckets`.

### Testing & CI

- [ ] **Integration tests** — Test against real cloud APIs (LocalStack for AWS, emulator for GCP) in CI.
- [x] **Coverage reporting** — Enforce minimum coverage threshold (80%) in `pyproject.toml`.
- [x] **GitHub Actions workflow** — Automated lint, test, type-check on push/PR.
- [x] **Type checking** — `mypy` config in `pyproject.toml`, runs in CI.

### Documentation

- [x] **API reference** — Auto-generated from docstrings via mkdocs + mkdocstrings. Run `uv run mkdocs serve`.
- [x] **Migration guide** — `docs/migration.md` — switching from raw SDKs to Cloudjack.
- [x] **Contributing guide** — `CONTRIBUTING.md` — standards for adding providers and services.
