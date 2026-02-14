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

- [ ] **Queue/Messaging** — Unified interface for AWS SQS, GCP Pub/Sub, Azure Service Bus.
- [ ] **IAM/Auth** — Role and policy management across providers.
- [ ] **DNS** — Route53, Cloud DNS, Azure DNS under one blueprint.
- [ ] **Compute** — Basic VM lifecycle (create, start, stop, terminate).
- [ ] **Logging** — CloudWatch Logs, Cloud Logging, Azure Monitor.

### Core Improvements

- [ ] **Async support** — Async variants of all service methods (`aiohttp`/`aioboto3`/`gcloud-aio`).
- [ ] **Connection pooling** — Reuse clients per provider+config to avoid redundant auth handshakes.
- [ ] **Retry policies** — Configurable retry/backoff strategy baked into the base blueprints.
- [ ] **Config validation** — Pydantic models for provider configs instead of raw dicts.
- [ ] **Credential chain** — Auto-resolve credentials from env vars, instance metadata, config files — not just explicit keys.
- [ ] **Logging & observability** — Structured logging on every API call with request IDs for tracing.

### Packaging & Distribution

- [ ] **Publish to PyPI** — Proper packaging with extras (`pip install cloudjack[aws]`, `cloudjack[gcp]`).
- [ ] **Optional dependencies** — Only install `boto3` if using AWS, `google-cloud-*` if using GCP.
- [ ] **CLI tool** — Thin CLI wrapper for common operations (e.g. `cloudjack secret get my_secret --provider aws`).

### Testing & CI

- [ ] **Integration tests** — Test against real cloud APIs (LocalStack for AWS, emulator for GCP) in CI.
- [ ] **Coverage reporting** — Enforce minimum coverage threshold in CI pipeline.
- [ ] **GitHub Actions workflow** — Automated lint, test, publish on tag.
- [ ] **Type checking** — Add `mypy --strict` to CI.

### Documentation

- [ ] **API reference** — Auto-generated from docstrings (Sphinx or mkdocs).
- [ ] **Migration guide** — How to switch from raw `boto3`/`google-cloud` to Cloudjack.
- [ ] **Contributing guide** — Standards for adding new providers and services.
