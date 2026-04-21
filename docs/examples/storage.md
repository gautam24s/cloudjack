# Storage — Examples

Covers AWS S3 and GCP Cloud Storage. Object keys, bucket names, and method signatures are identical across providers.

## Buckets

```python
from cloudjack import universal_factory

storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

storage.create_bucket("my-bucket")
storage.list_buckets()         # -> list[str]
storage.delete_bucket("my-bucket")   # bucket must be empty
```

## Upload / download

```python
# Upload a local file
storage.upload_object_from_file("my-bucket", "data/report.csv", "/tmp/report.csv")

# Upload an in-memory bytes payload
storage.upload_object_from_bytes("my-bucket", "data/blob.bin", b"\x00\x01\x02")

# Download to a local path
storage.download_file("my-bucket", "data/report.csv", "/tmp/report-copy.csv")

# Read bytes directly (no local file)
blob: bytes = storage.get_object("my-bucket", "data/report.csv")
```

## List with a prefix

```python
# All objects
keys = storage.list_objects("my-bucket")

# Keys under a virtual "folder"
csv_keys = storage.list_objects("my-bucket", prefix="data/")
```

## Delete objects

```python
storage.delete_object("my-bucket", "data/report.csv")

# Bulk delete
for key in storage.list_objects("my-bucket", prefix="tmp/"):
    storage.delete_object("my-bucket", key)
```

## Signed URLs

```python
# Download link valid for 1 hour
url = storage.generate_signed_url("my-bucket", "report.csv", expiration=3600)

# Upload link (PUT request)
upload_url = storage.generate_signed_url(
    "my-bucket",
    "uploads/photo.jpg",
    expiration=600,
    method="PUT",
    content_type="image/jpeg",
)
```

Provider-specific keyword arguments are forwarded. GCP also accepts `version="v4"` (default) and `scheme="https"`.

## Idempotent bucket create

```python
from cloudjack import BucketAlreadyExistsError

try:
    storage.create_bucket("my-bucket")
except BucketAlreadyExistsError:
    pass  # already there, we're good
```

## Empty-then-delete a bucket

Both AWS and GCP require buckets to be empty before deletion. This helper handles any number of objects:

```python
def empty_and_delete(storage, bucket: str) -> None:
    for key in storage.list_objects(bucket):
        storage.delete_object(bucket, key)
    storage.delete_bucket(bucket)
```

## Cross-cloud copy

Copy one object from AWS to GCP using in-memory bytes (fine for small/medium objects; stream via the provider SDK directly for very large ones):

```python
from cloudjack import universal_factory

aws = universal_factory("storage", "aws", {"region_name": "us-east-1"})
gcp = universal_factory("storage", "gcp", {"project_id": "my-project"})

blob = aws.get_object("src-bucket", "data.csv")
gcp.upload_object_from_bytes("dst-bucket", "data.csv", blob)
```

## Concurrent uploads (async)

`asyncio.gather` runs every upload in a worker thread — the event loop never blocks on I/O:

```python
import asyncio
from pathlib import Path

async def upload_many(storage, bucket: str, files: list[Path]) -> None:
    await asyncio.gather(*(
        storage.aupload_object_from_file(bucket, f.name, str(f))
        for f in files
    ))

asyncio.run(upload_many(storage, "my-bucket", list(Path("/data").glob("*.csv"))))
```

## Exception branching

```python
from cloudjack import BucketNotFoundError, ObjectNotFoundError, StorageError

try:
    storage.get_object("missing-bucket", "key")
except BucketNotFoundError:
    ...
except ObjectNotFoundError:
    ...
except StorageError:
    # any other storage API failure
    ...
```

## CLI

```bash
cloudjack -p aws -s storage list-buckets
cloudjack -p aws -s storage upload-file my-bucket key /path/to/file
cloudjack -p gcp -s storage list-objects my-bucket -c '{"project_id":"p"}'
```
