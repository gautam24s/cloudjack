# Contributing to Cloudjack

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/cloudjack.git
cd cloudjack

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install all dependencies
uv sync --dev
```

## Project Structure

```
cloudjack/
├── base/           # Abstract service interfaces and core utilities
│   ├── compute.py
│   ├── dns.py
│   ├── iam.py
│   ├── logging_service.py
│   ├── queue.py
│   ├── secret_manager.py
│   ├── storage.py
│   ├── config.py        # Pydantic config models
│   ├── retry.py         # Retry decorator
│   ├── client_cache.py  # Connection pooling
│   ├── async_support.py # Async wrappers
│   ├── logger.py        # Structured logging
│   └── exceptions.py    # Exception hierarchy
├── aws/            # AWS implementations
├── gcp/            # GCP implementations
├── factory.py      # Universal factory
└── cli.py          # CLI entrypoint
tests/              # Unit tests (pytest)
```

## Adding a New Service

1. **Create the service interface** in `cloudjack/base/<service>.py` — define an ABC (named `<Name>Service`) with abstract methods.
2. **Add exceptions** to `cloudjack/base/exceptions.py`.
3. **Implement for AWS** in `cloudjack/aws/<service>.py`.
4. **Implement for GCP** in `cloudjack/gcp/<service>.py`.
5. **Register** the service in `cloudjack/aws/factory.py` and `cloudjack/gcp/factory.py`.
6. **Add an `@overload`** to `cloudjack/factory.py`.
7. **Export** the service interface from `cloudjack/base/__init__.py`.
8. **Write tests** in `tests/test_aws_<service>.py` and `tests/test_gcp_<service>.py`.

## Adding a New Provider

1. Create `cloudjack/<provider>/` with an `__init__.py` and `factory.py`.
2. Implement each service interface.
3. Register the provider in `cloudjack/factory.py`'s `_PROVIDER_MODULES`.
4. Register a matching Pydantic config model in `cloudjack/base/config.py`'s `CONFIG_REGISTRY` and extend `existing_cloud_providers` in `cloudjack/base/supported_services.py`.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=cloudjack --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_aws_storage.py -v
```

## Type Checking

```bash
uv run mypy cloudjack/ --ignore-missing-imports
```

## Code Style

- Use type annotations for all function signatures.
- Follow existing patterns for error handling (`_ERROR_MAP` + `_handle` helpers).
- Write docstrings for all public methods.
- Keep implementations concise — delegate to the SDK, don't over-abstract.

## Pull Request Checklist

- [ ] All existing tests pass (`uv run pytest`)
- [ ] New tests cover the added/changed code
- [ ] Type annotations are present
- [ ] Docstrings are written for public API
- [ ] Factories and `__init__.py` exports are updated
- [ ] No credentials or secrets in the code

## Commit Messages

Use conventional commits:

```
feat: add Azure Blob Storage implementation
fix: handle pagination in SQS list_queues
docs: update README with DNS examples
test: add missing edge cases for IAM
```
