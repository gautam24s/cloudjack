# Examples

Working code for the common tasks you'll do with Cloudjack. Every example uses the real method signatures, and each service page shows both the AWS and GCP variant side-by-side so you can see that the same code runs against either provider.

## By service

- [Secret Manager](secret_manager.md) — read, write, rotate, sync secrets across clouds.
- [Storage](storage.md) — buckets, objects, uploads, downloads, signed URLs, bulk copy.
- [Queue](queue.md) — producers, long-poll consumers, fan-out workers.
- [Compute](compute.md) — launch, inspect, bulk-stop VMs.
- [DNS](dns.md) — zones, records, bulk updates, migrating between providers.
- [IAM](iam.md) — role + policy management, attaching/detaching.
- [Logging](logging.md) — log groups, structured writes, filtered reads.

## Cross-cutting patterns

- [Configuration](config.md) — env vars, explicit dicts, pre-built `AWSConfig` / `GCPConfig`.
- [Async](async.md) — awaiting the auto-generated `a<method>` variants, gathering concurrent calls.
- [Errors](errors.md) — catching provider-agnostic exceptions, branching by subclass.
- [Retry](retry.md) — decorating calls with exponential backoff.
- [Cookbook](cookbook.md) — end-to-end recipes (daily backup, cross-cloud sync, deploy-and-secure).

## Setup assumed by these pages

All examples assume the following scaffolding. Copy it once at the top of your file:

```python
from cloudjack import universal_factory, AWSConfig, GCPConfig

AWS = {
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "region_name": "us-east-1",
}
GCP = {"project_id": "my-gcp-project"}
```

Or rely on environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`) and omit the `config` argument entirely — the SDK credential chain handles the rest.
