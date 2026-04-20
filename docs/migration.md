# Migration Guide

## Migrating from Direct SDK Usage to Cloudjack

This guide shows how to replace direct boto3 / google-cloud calls with
Cloudjack's unified interface.

---

### Storage — AWS S3

**Before (boto3):**

```python
import boto3

s3 = boto3.client("s3",
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1",
)
s3.create_bucket(Bucket="my-bucket")
s3.upload_file("local.txt", "my-bucket", "remote.txt")
buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
```

**After (Cloudjack):**

```python
from cloudjack import universal_factory

storage = universal_factory("storage", "aws", {
    "aws_access_key_id": "AKIA...",
    "aws_secret_access_key": "...",
    "region_name": "us-east-1",
})
storage.create_bucket("my-bucket")
storage.upload_file("my-bucket", "remote.txt", "local.txt")
buckets = storage.list_buckets()
```

---

### Storage — GCP Cloud Storage

**Before (google-cloud-storage):**

```python
from google.cloud import storage

client = storage.Client(project="my-project")
bucket = client.create_bucket("my-bucket")
blob = bucket.blob("remote.txt")
blob.upload_from_filename("local.txt")
buckets = [b.name for b in client.list_buckets()]
```

**After (Cloudjack):**

```python
from cloudjack import universal_factory

storage = universal_factory("storage", "gcp", {"project_id": "my-project"})
storage.create_bucket("my-bucket")
storage.upload_file("my-bucket", "remote.txt", "local.txt")
buckets = storage.list_buckets()
```

---

### Switching Providers

The biggest advantage: swap one string to change providers.

```python
provider = "aws"  # or "gcp"
storage = universal_factory("storage", provider, config[provider])

# Same API regardless of provider
storage.create_bucket("my-bucket")
storage.upload_file("my-bucket", "key", "/path/to/file")
```

---

### Secret Manager

**Before (boto3):**

```python
sm = boto3.client("secretsmanager", ...)
sm.create_secret(Name="my-secret", SecretString="value")
resp = sm.get_secret_value(SecretId="my-secret")
value = resp["SecretString"]
```

**After:**

```python
sm = universal_factory("secret_manager", "aws", config)
sm.create_secret("my-secret", "value")
value = sm.get_secret("my-secret")
```

---

### Queue / Messaging

**Before (boto3 SQS):**

```python
sqs = boto3.client("sqs", ...)
resp = sqs.create_queue(QueueName="tasks")
url = resp["QueueUrl"]
sqs.send_message(QueueUrl=url, MessageBody="hello")
```

**After:**

```python
queue = universal_factory("queue", "aws", config)
url = queue.create_queue("tasks")
queue.send_message(url, "hello")
```

---

### Exception Handling

Cloudjack provides provider-agnostic exceptions:

```python
from cloudjack.base.exceptions import BucketNotFoundError, StorageError

try:
    storage.delete_bucket("missing")
except BucketNotFoundError:
    print("Bucket does not exist")
except StorageError as e:
    print(f"Storage error: {e}")
```

No need to catch `botocore.exceptions.ClientError` or
`google.api_core.exceptions.NotFound` directly.

---

### Config Validation (Optional)

`universal_factory` accepts either a `dict` or a pre-built
[`AWSConfig`][cloudjack.base.config.AWSConfig] /
[`GCPConfig`][cloudjack.base.config.GCPConfig] instance. Dicts go through
Pydantic validation; model instances pass through unchanged (after a
provider-match check). Build the config once and reuse it across every
service to keep a single cached client per provider.

```python
from cloudjack import AWSConfig, universal_factory

cfg = AWSConfig(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1",
)

storage = universal_factory("storage", "aws", cfg)
queue   = universal_factory("queue",   "aws", cfg)
sm      = universal_factory("secret_manager", "aws", cfg)
```

Passing a `GCPConfig` with `cloud_provider="aws"` (or vice versa) raises
`TypeError` at call time.

Environment variables are used as fallbacks automatically
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`,
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`), and anything
still missing delegates to the provider SDK's credential chain.

---

## Upgrading from 0.2.x → 0.3.0

- The seven service interface ABCs are renamed from `*Blueprint` to
  `*Service` — e.g. `CloudStorageBlueprint` → `StorageService`. Users
  going through `universal_factory` don't need to change anything;
  direct importers of `cloudjack.base.*Blueprint` must rename.
- `universal_factory` now accepts `AWSConfig` / `GCPConfig` instances in
  addition to raw dicts (as shown above). Dict callers are unaffected.

## Upgrading from 0.1.x → 0.2.0

- The abstract interface classes are no longer re-exported from the
  top-level `cloudjack` (formerly `cloud`) package. If you were doing
  `from cloud import CloudStorageBlueprint`, switch to accessing clients
  via `universal_factory` only — the return type is inferred from the
  service literal.
