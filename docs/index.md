# Cloudjack

A unified Python SDK for interacting with cloud services across multiple providers (AWS, GCP) through a single, consistent interface.

## Why Cloudjack?

- **One API** — Write code once, run on any supported cloud.
- **Type-safe** — `@overload` signatures give your IDE full autocomplete on returned service objects.
- **Extensible** — Add new providers and services by implementing an ABC and registering in the factory.
- **Production-ready** — Built-in retry, connection pooling, structured logging, config validation, and async support.

## Quick Example

```python
from cloud import universal_factory

# AWS S3
storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})
storage.create_bucket("my-bucket")
storage.upload_file("my-bucket", "hello.txt", "/tmp/hello.txt")

# GCP Cloud Storage — same interface
storage = universal_factory("storage", "gcp", {"project_id": "my-project"})
storage.create_bucket("my-bucket")
```

## Supported Services

| Service | AWS | GCP |
|---|---|---|
| Secret Manager | Secrets Manager | Secret Manager |
| Storage | S3 | Cloud Storage |
| Queue | SQS | Pub/Sub |
| Compute | EC2 | Compute Engine |
| DNS | Route 53 | Cloud DNS |
| IAM | IAM | IAM Admin |
| Logging | CloudWatch Logs | Cloud Logging |

## Install

```bash
pip install cloudjack[aws]    # AWS only
pip install cloudjack[gcp]    # GCP only
pip install cloudjack[all]    # Both
```
