# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Cloudjack is a Python SDK (published to PyPI) that exposes a unified interface over AWS and GCP. The public surface is one function — `cloud.factory.universal_factory` — which returns a provider-specific service instance that conforms to a shared abstract blueprint. Seven services are supported: `secret_manager`, `storage`, `queue`, `compute`, `dns`, `iam`, `logging`.

## Commands

Dependency management and execution go through `uv` (the project is set up with `uv sync --dev`).

```bash
uv sync --dev                                     # install all dev deps
uv run pytest                                     # full test suite
uv run pytest tests/test_aws_storage.py -v        # single file
uv run pytest tests/test_aws_storage.py::TestStorage::test_create_bucket  # single test
uv run pytest --cov=cloud --cov-report=term-missing   # with coverage (fail_under=80)
uv run mypy cloud/ --ignore-missing-imports       # type-check
uv build                                          # build sdist + wheel
./publish.sh [patch|minor|major|<version>]        # test, build, upload to PyPI, tag (needs PYPI_TOKEN)
```

The CLI entrypoint `cloudjack` (registered in `pyproject.toml` → `cloud.cli:main`) runs any service method from the shell, e.g. `cloudjack --provider aws --service storage list-buckets`. Dash-separated operation names are mapped to underscore method names inside `cli.py`.

## Architecture

### Blueprint + registry pattern

Every service has three layers:

1. **`cloud/base/<service>.py`** — an `ABC` blueprint that defines the cross-provider method signatures (e.g. `CloudStorageBlueprint`, `QueueBlueprint`). Exported from `cloud/base/__init__.py`.
2. **`cloud/aws/<service>.py` and `cloud/gcp/<service>.py`** — concrete subclasses that wrap the provider SDK (boto3 / google-cloud-*). Each provider file defines a local `_ERROR_MAP` dict and a `_handle_*` helper that translates SDK errors into the shared exception hierarchy in `cloud/base/exceptions.py` (`CloudjackError` is the root).
3. **`cloud/aws/factory.py` and `cloud/gcp/factory.py`** — each exports a `SERVICE_REGISTRY: dict[str, type]` mapping the service name to its class.

`cloud/factory.py` holds `_FACTORY_REGISTRY: {"aws": AWS_SERVICES, "gcp": GCP_SERVICES}` and the `universal_factory` dispatcher. It declares one `@overload` per service so IDEs infer the precise blueprint return type from the `service_name` literal — when you add a service, add a matching overload here or callers lose typing.

The provider/service literals live in `cloud/base/supported_services.py` (`existing_services`, `existing_cloud_providers`). Update both these Literal types and the registries when adding anything new.

### Caching and config flow

`universal_factory` does **not** instantiate the service directly. It runs `validate_config(cloud_provider, config)` to get a Pydantic model (`AWSConfig` / `GCPConfig` in `cloud/base/config.py`), then routes through `ClientCache().get_or_create(...)`. The cache key is a SHA-256 hash of `{provider, service, config.model_dump()}` so identical config dicts share a single instance process-wide. This caching path is load-bearing — see the "Client Caching ignored" note in the README (it was a regression). Don't bypass it.

Config models use `model_validator(mode="before")` to fall back to environment variables (`AWS_ACCESS_KEY_ID`, `GOOGLE_CLOUD_PROJECT`, etc.) and leave fields `None` otherwise so the SDK credential chains (instance metadata, ADC) still work. `GCPConfig` additionally requires `project_id` and will load a service-account JSON from `credentials_path` lazily.

### Cross-cutting utilities in `cloud/base/`

- `async_support.py` — `async_wrap` turns a sync method into a coroutine via `asyncio.to_thread`. `AsyncMixin.__init_subclass__` auto-generates `a<method>` variants at class-definition time for every public callable not already async. To expose async versions of a new method, inherit from `AsyncMixin` alongside the blueprint.
- `client_cache.py` — thread-safe singleton; `ClientCache()` always returns the same instance. `clear()` exists for tests.
- `retry.py` — `@retry(...)` decorator with exponential backoff. Default retryable set is `(ConnectionError, TimeoutError, OSError)`; pass `retryable_exceptions=` to override per call site.
- `logger.py` — structured JSON logger (module logger `cloudjack`).

### Adding a service

Follow these steps in order (the `@overload` and Literal updates are easy to miss):

1. Blueprint in `cloud/base/<service>.py` + export from `cloud/base/__init__.py`.
2. Exceptions in `cloud/base/exceptions.py`.
3. Implementations in `cloud/aws/<service>.py` and `cloud/gcp/<service>.py` (follow the `_ERROR_MAP` + `_handle_*` pattern).
4. Register the class in both provider `factory.py` files' `SERVICE_REGISTRY`.
5. Add `@overload` in `cloud/factory.py` and extend `existing_services` in `cloud/base/supported_services.py`.
6. Tests in `tests/test_aws_<service>.py` and `tests/test_gcp_<service>.py`.

### Adding a provider

Create `cloud/<provider>/` with its own `factory.py` exporting `SERVICE_REGISTRY`, add an entry to `_FACTORY_REGISTRY` in `cloud/factory.py`, register a matching Pydantic model in `CONFIG_REGISTRY` inside `cloud/base/config.py`, and extend `existing_cloud_providers`. There is an empty `cloud/azure/` directory — Azure support is on the roadmap, not implemented.

## Conventions

- Python >= 3.10, tested through 3.14. Use `from __future__ import annotations` where already present and modern generics (`dict[str, X]`, `X | None`).
- Provider implementations should stay thin — delegate to the SDK and only abstract what the blueprint requires. Map SDK error codes to the shared exception hierarchy rather than leaking `ClientError` / Google API exceptions.
- `mypy` is configured with `warn_return_any = true`; GCP responses often have `Any` properties, so cast explicitly to `str` etc. when the blueprint promises a concrete type (see the fix note in the README for `gcp/iam.py`, `gcp/secret_manager.py`).
- Commit messages follow conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
