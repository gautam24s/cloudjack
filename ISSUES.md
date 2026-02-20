# Cloudjack — Known Issues

Tracking document for codebase issues. Items are checked off as they are resolved.

---

## Critical / Bugs

- [x] **1. `GCPConfig.project_id` can be `None` but services use it as `str`**
  All GCP services assign `self.project_id: str = config.project_id`, but `GCPConfig.project_id` is typed `str | None`. If no project ID is provided and no env var is set, this silently becomes `None`, causing runtime failures deep in SDK calls instead of failing fast at init.
  - **Files:** `cloud/gcp/compute.py`, `cloud/gcp/dns.py`, `cloud/gcp/iam.py`, `cloud/gcp/logging_service.py`, `cloud/gcp/queue.py`, `cloud/gcp/secret_manager.py`, `cloud/gcp/storage.py`
  - **Fix:** Added `@model_validator(mode="after")` in `GCPConfig` that raises `ValueError` if `project_id` is `None`.

- [x] **2. `GCPConfig.credentials_path` is resolved but never used**
  `cloud/base/config.py` resolves `GOOGLE_APPLICATION_CREDENTIALS` into `credentials_path`, but no GCP service reads `config.credentials_path` to load credentials from the file. The field is dead config — users who set `GOOGLE_APPLICATION_CREDENTIALS` might expect it to work through cloudjack, but it only works if the GCP SDK picks it up independently.
  - **Fix:** Added logic in `GCPConfig` after-validator to load credentials from `credentials_path` via `google.oauth2.service_account.Credentials.from_service_account_file()`.

- [x] **3. `ClientCache` is not thread-safe despite docstring claim**
  `cloud/base/client_cache.py` says "Thread-safe, in-process cache" but uses a plain `dict` with no locking. Concurrent `get_or_create` calls can create duplicate instances or see partial state.
  - **Fix:** Added `threading.Lock` and wrapped `get_or_create` / `clear` with `with self._lock:`.

- [x] **4. `main.py` will crash on startup**
  `main.py` passes `{"region": "us-west-1", "credentials": "aws_creds"}` to `universal_factory` for AWS, but `AWSConfig` expects `region_name`, `aws_access_key_id`, `aws_secret_access_key`. The key `"region"` will be silently ignored and `"credentials"` is not a valid field.
  - **Fix:** Updated `main.py` to use correct `AWSConfig` field names.

---

## Medium / Design Issues

- [x] **5. GCP services don't pass `credentials` to SDK clients**
  AWS services consistently pass explicit credentials to boto3. But most GCP services ignore `config.credentials`:
  - `cloud/gcp/compute.py` — `compute_v1.InstancesClient()` — no credentials passed
  - `cloud/gcp/dns.py` — `cloud_dns.Client(project=...)` — no credentials passed
  - `cloud/gcp/iam.py` — `iam_admin_v1.IAMClient()` — no credentials passed
  - `cloud/gcp/logging_service.py` — `cloud_logging.Client(project=...)` — no credentials passed
  - `cloud/gcp/queue.py` — `PublisherClient()` / `SubscriberClient()` — no credentials passed

  Only `cloud/gcp/secret_manager.py` and `cloud/gcp/storage.py` pass `credentials`.
  - **Fix:** Added `credentials=config.credentials` to all 5 GCP service client constructors.

- [x] **6. AWS `list_zones` / `list_log_groups` / `list_roles` / `list_policies` don't paginate**
  - `cloud/aws/dns.py` — `list_hosted_zones()` returns only the first page (max 100 zones).
  - `cloud/aws/logging_service.py` — `describe_log_groups()` returns only first page.
  - `cloud/aws/iam.py` — `list_roles()` returns only first page.
  - `cloud/aws/iam.py` — `list_policies()` returns only first page.

  In contrast, `list_objects` in `cloud/aws/storage.py` correctly uses a paginator.
  - **Fix:** Replaced direct API calls with `client.get_paginator()` in all 4 methods. Updated corresponding tests.

- [x] **7. AWS `read_logs` severity is hardcoded**
  `cloud/aws/logging_service.py` — severity is always `"INFO"` regardless of actual log content. The `write_log` method prepends `[{severity}]` to the message, but `read_logs` doesn't parse it back out.
  - **Fix:** `read_logs` now parses the `[SEVERITY] message` format to extract severity and clean message.

- [x] **8. `cloud/__init__.py` only exports `SecretManagerBlueprint`**
  Exports `SecretManagerBlueprint` and `universal_factory` but not `CloudStorageBlueprint`, `QueueBlueprint`, `ComputeBlueprint`, `DNSBlueprint`, `IAMBlueprint`, or `LoggingBlueprint`. Users importing from `cloud` directly will only see a partial API.
  - **Fix:** Exported all 7 blueprints in `__all__`.

- [x] **9. `cloud/aws/__init__.py` and `cloud/gcp/__init__.py` only export 2 of 7 services**
  Both only export `SecretManager` and `Storage` in `__all__`, missing `Queue`, `Compute`, `DNS`, `IAM`, `Logging`.
  - **Fix:** Exported all 7 services in both `__init__.py` files.

- [x] **10. `GCPConfig` not validated by Pydantic for extra fields**
  `AWSConfig` and `GCPConfig` use Pydantic defaults that allow extra fields silently. Typos like `region` instead of `region_name` will not raise validation errors.
  - **Fix:** Added `model_config = ConfigDict(extra="forbid")` to both `AWSConfig` and `GCPConfig`.

---

## Low / Code Quality

- [x] **11. `InstanceAlreadyExistsError` imported inline in GCP compute**
  `cloud/gcp/compute.py` — imported inside the `except` block rather than at the top with other imports.
  - **Fix:** Moved import to top-level with other exception imports.

- [x] **12. `retry` decorator has unreachable final `raise`**
  `cloud/base/retry.py` — `raise last_exc` after the for loop is technically unreachable. The `# type: ignore[misc]` comment confirms this.
  - **Fix:** Replaced with a guarded `raise RuntimeError(...)` with `# pragma: no cover`. Removed unused `last_exc` variable.

- [x] **13. `CloudjackLogger` handler duplication risk**
  `cloud/base/logger.py` — checks `if not self.logger.handlers` but `CloudjackLogger` is not a singleton. Multiple instances with the same name share the stdlib logger, making the check work but the design fragile.
  - **Fix:** Added class-level `_initialised_loggers: set[str]` to track which logger names have been configured, preventing handler duplication.

- [x] **14. `generate_signed_url` in base blueprint uses untyped `**kwargs`**
  `cloud/base/storage.py` — `**kwargs` parameter is not typed (`**kwargs` instead of `**kwargs: Any`), inconsistent with all other blueprints.
  - **Fix:** Changed to `**kwargs: Any` and added `from typing import Any` import.

- [x] **15. `SecretManagerBlueprint` methods have redundant `pass` bodies**
  `cloud/base/secret_manager.py` — all abstract methods have explicit `pass` statements after docstrings, unlike the other blueprints.
  - **Fix:** Removed all redundant `pass` statements.

- [x] **16. No `__all__` in `cloud/base/config.py`**
  The config module exports `AWSConfig`, `GCPConfig`, `CONFIG_REGISTRY`, and `validate_config` but has no `__all__` to declare the public API.
  - **Fix:** Added `__all__` with all 4 public symbols.
