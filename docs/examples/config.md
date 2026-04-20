# Configuration — Examples

`universal_factory` accepts `config` in three forms. Pick the one that matches how you produce the values.

## 1. Raw dict (simplest)

```python
from cloudjack import universal_factory

aws = universal_factory("storage", "aws", {
    "aws_access_key_id": "AKIA...",
    "aws_secret_access_key": "...",
    "region_name": "us-east-1",
})

gcp = universal_factory("storage", "gcp", {"project_id": "my-project"})
```

Dict keys match the field names on `AWSConfig` / `GCPConfig`. Unknown keys raise a validation error (`extra="forbid"`).

## 2. Environment variables (no config)

Drop the `config` argument and Cloudjack falls back to env vars, then to the provider SDK's default credential chain (EC2 IMDS, `~/.aws/credentials`, ADC, etc.).

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"

export GOOGLE_CLOUD_PROJECT="my-project"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"
```

```python
storage = universal_factory("storage", "aws")
gcp     = universal_factory("storage", "gcp")
```

You can mix: pass `{"region_name": "eu-west-1"}` and let the credentials resolve from the environment.

## 3. Pre-built config model (0.3.0+)

Build the Pydantic model once and pass the instance. Useful when the same config goes to multiple services — you avoid re-validation, and identical configs share a single cached client per provider.

```python
from cloudjack import universal_factory, AWSConfig

cfg = AWSConfig(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1",
)

storage = universal_factory("storage", "aws", cfg)
queue   = universal_factory("queue",   "aws", cfg)
sm      = universal_factory("secret_manager", "aws", cfg)
```

Passing a mismatched model type (e.g. `GCPConfig` with `cloud_provider="aws"`) raises `TypeError` at call time.

## GCP: credentials JSON file

`GCPConfig.credentials_path` accepts a path to a service-account JSON file and loads it lazily when the service is instantiated:

```python
from cloudjack import universal_factory, GCPConfig

cfg = GCPConfig(
    project_id="my-project",
    credentials_path="/etc/secrets/sa.json",
)
storage = universal_factory("storage", "gcp", cfg)
```

If `credentials_path` is omitted, Cloudjack checks `GOOGLE_APPLICATION_CREDENTIALS`, and finally falls back to Application Default Credentials.

## GCP: in-memory credentials

For test harnesses or services that build credentials dynamically, pass a `google.auth.credentials.Credentials` object directly:

```python
from google.oauth2 import service_account
from cloudjack import universal_factory, GCPConfig

creds = service_account.Credentials.from_service_account_info(JSON_DICT)
cfg = GCPConfig(project_id="my-project", credentials=creds)
storage = universal_factory("storage", "gcp", cfg)
```

## Cache interaction

Two calls with equivalent configs share the same cached service instance:

```python
from cloudjack import universal_factory

a = universal_factory("storage", "aws", {"region_name": "us-east-1"})
b = universal_factory("storage", "aws", {"region_name": "us-east-1"})
assert a is b   # ✔ same cached instance

c = universal_factory("storage", "aws", {"region_name": "eu-west-1"})
assert a is not c   # ✔ different region → different cache key
```

`{"region_name": None}` and `{}` hash to the same key because the cache serialises with `exclude_none=True`.

## Clear the cache (testing)

```python
from cloudjack.base.client_cache import ClientCache

ClientCache().clear()
```

## Validate without instantiating

Useful in config loaders / startup checks:

```python
from cloudjack.base.config import validate_config, AWSConfig

raw = {
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "region_name": "us-east-1",
}
cfg: AWSConfig = validate_config("aws", raw)
```

A bad key or type raises `pydantic.ValidationError`.
