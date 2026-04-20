# Secret Manager — Examples

Covers AWS Secrets Manager and GCP Secret Manager through the same API.

## Basic CRUD

=== "AWS"

    ```python
    from cloudjack import universal_factory

    sm = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})

    # Create
    sm.create_secret("db/password", "s3cr3t")

    # Read
    value = sm.get_secret("db/password")

    # Update (stores a new version)
    sm.update_secret("db/password", "rotated-value")

    # Delete
    sm.delete_secret("db/password")
    ```

=== "GCP"

    ```python
    from cloudjack import universal_factory

    sm = universal_factory("secret_manager", "gcp", {"project_id": "my-project"})

    sm.create_secret("db-password", "s3cr3t")      # GCP secret IDs cannot contain '/'
    value = sm.get_secret("db-password")
    sm.update_secret("db-password", "rotated-value")
    sm.delete_secret("db-password")
    ```

## Idempotent create

`create_secret` raises `SecretAlreadyExistsError` if the secret exists. Catch it to make the call idempotent:

```python
from cloudjack import SecretAlreadyExistsError

try:
    sm.create_secret("db-password", "value")
except SecretAlreadyExistsError:
    sm.update_secret("db-password", "value")
```

## Rotation pattern

Generate a new credential, write it, then read it back to confirm:

```python
import secrets
from cloudjack import universal_factory

sm = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})

new_value = secrets.token_urlsafe(32)
sm.update_secret("db-password", new_value)

# Verify it was stored
assert sm.get_secret("db-password") == new_value
```

## Bootstrap secret if missing

```python
from cloudjack import SecretNotFoundError

def ensure_secret(sm, name: str, default_value: str) -> str:
    try:
        return sm.get_secret(name)
    except SecretNotFoundError:
        sm.create_secret(name, default_value)
        return default_value

api_key = ensure_secret(sm, "api-key", "generated-on-first-run")
```

## Sync a secret across providers

Useful when you run a service on both AWS and GCP and need the same secret value in both stores:

```python
from cloudjack import universal_factory, SecretNotFoundError

aws_sm = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})
gcp_sm = universal_factory("secret_manager", "gcp", {"project_id": "my-project"})

def sync(source, dest, name: str) -> None:
    value = source.get_secret(name)
    try:
        dest.update_secret(name, value)
    except SecretNotFoundError:
        dest.create_secret(name, value)

sync(aws_sm, gcp_sm, "db-password")
```

## Async (concurrent reads)

```python
import asyncio
from cloudjack import universal_factory

sm = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})

async def load_all(names: list[str]) -> dict[str, str]:
    values = await asyncio.gather(*(sm.aget_secret(n) for n in names))
    return dict(zip(names, values))

asyncio.run(load_all(["db/password", "redis/password", "api-key"]))
```

## CLI

```bash
cloudjack -p aws -s secret_manager create-secret my-secret s3cr3t
cloudjack -p aws -s secret_manager get-secret my-secret
cloudjack -p gcp -s secret_manager get-secret -c '{"project_id":"p"}' my-secret
```
