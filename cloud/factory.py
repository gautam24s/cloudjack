"""Universal service factory.

Provides :func:`universal_factory`, the single entry-point for creating
cloud service clients.  The function dispatches to provider-specific
factories (AWS, GCP) based on ``cloud_provider`` and returns a typed
instance via ``@overload`` signatures so IDEs can autocomplete methods.

Provider modules are loaded **lazily** — importing ``cloud`` does not
pull in ``boto3`` or ``google-cloud-*``.  Each provider is imported the
first time a service is requested for it, so installing only one extra
(e.g. ``pip install cloudjack[aws]``) is enough when only that provider
is used.
"""

from __future__ import annotations

import importlib
from typing import Literal, overload

from cloud.base import (
    StorageService,
    ComputeService,
    DNSService,
    IAMService,
    LoggingService,
    QueueService,
    SecretManagerService,
    existing_cloud_providers,
    existing_services,
)
from cloud.base.client_cache import ClientCache
from cloud.base.config import AWSConfig, GCPConfig, validate_config

# Accepted shapes for the ``config`` parameter.  Dicts are validated through
# the Pydantic models; already-validated :class:`AWSConfig` / :class:`GCPConfig`
# instances are used as-is so callers who construct them explicitly don't
# pay re-validation cost.
ConfigInput = dict | AWSConfig | GCPConfig | None


# Provider → (module path, install-extra name). The module must export a
# ``SERVICE_REGISTRY: dict[str, type]`` at top level.
_PROVIDER_MODULES: dict[str, tuple[str, str]] = {
    "aws": ("cloud.aws.factory", "aws"),
    "gcp": ("cloud.gcp.factory", "gcp"),
}

# Cache of resolved service registries so we only import each provider once.
_registry_cache: dict[str, dict[str, type]] = {}


def _load_service_registry(cloud_provider: str) -> dict[str, type]:
    """Import the provider factory on demand and return its SERVICE_REGISTRY.

    Raises:
        ValueError: If the provider is unknown.
        ImportError: If the provider module cannot be imported because its
            optional SDK dependencies are missing. The error message tells
            the caller which extra to install.
    """
    cached = _registry_cache.get(cloud_provider)
    if cached is not None:
        return cached

    entry = _PROVIDER_MODULES.get(cloud_provider)
    if entry is None:
        raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
    module_path, extra = entry

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Cloud provider '{cloud_provider}' is not installed. "
            f"Install the optional dependency group with: "
            f"pip install 'cloudjack[{extra}]'  "
            f"(underlying import error: {exc})"
        ) from exc

    registry: dict[str, type] = module.SERVICE_REGISTRY
    _registry_cache[cloud_provider] = registry
    return registry


def _resolve_config(
    cloud_provider: str, config: ConfigInput
) -> AWSConfig | GCPConfig:
    """Coerce *config* to the provider's Pydantic model.

    Pre-validated :class:`AWSConfig` / :class:`GCPConfig` instances are
    returned unchanged (with a provider-match check); dicts and ``None`` go
    through :func:`validate_config`.
    """
    if isinstance(config, (AWSConfig, GCPConfig)):
        expected = AWSConfig if cloud_provider == "aws" else GCPConfig
        if not isinstance(config, expected):
            raise TypeError(
                f"config must be {expected.__name__} for "
                f"cloud_provider={cloud_provider!r}, "
                f"got {type(config).__name__}"
            )
        return config
    return validate_config(cloud_provider, config)


@overload
def universal_factory(
    service_name: Literal["secret_manager"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> SecretManagerService: ...


@overload
def universal_factory(
    service_name: Literal["storage"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> StorageService: ...


@overload
def universal_factory(
    service_name: Literal["queue"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> QueueService: ...


@overload
def universal_factory(
    service_name: Literal["compute"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> ComputeService: ...


@overload
def universal_factory(
    service_name: Literal["dns"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> DNSService: ...


@overload
def universal_factory(
    service_name: Literal["iam"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> IAMService: ...


@overload
def universal_factory(
    service_name: Literal["logging"],
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> LoggingService: ...


def universal_factory(
    service_name: existing_services,
    cloud_provider: existing_cloud_providers,
    config: ConfigInput = None,
) -> (
    SecretManagerService
    | StorageService
    | QueueService
    | ComputeService
    | DNSService
    | IAMService
    | LoggingService
):
    """Create a cloud service client.

    The matching provider module is imported on demand, so projects that
    only install one extra (``cloudjack[aws]`` or ``cloudjack[gcp]``) do
    not need the other provider's SDK to be present.

    Args:
        service_name: Service identifier (``secret_manager``, ``storage``,
            ``queue``, ``compute``, ``dns``, ``iam``, ``logging``).
        cloud_provider: Cloud provider (``aws`` or ``gcp``).
        config: Optional configuration. Accepts either a raw ``dict`` (which
            is validated against the provider's Pydantic model) or a ready
            :class:`AWSConfig` / :class:`GCPConfig` instance (used as-is).
            Missing fields fall back to environment variables and the
            provider SDK's default credential chain.

    Returns:
        A cached service instance for the requested service.

    Raises:
        ValueError: If the cloud provider or service is not supported.
        TypeError: If *config* is a validated model that doesn't match the
            *cloud_provider* (e.g. passing a GCPConfig for the AWS provider).
        ImportError: If the provider's optional dependencies are missing.
            Install with ``pip install 'cloudjack[<provider>]'``.
    """
    provider_services = _load_service_registry(cloud_provider)

    if service_name not in provider_services:
        raise ValueError(
            f"Unsupported service '{service_name}' for provider '{cloud_provider}'"
        )

    service_class = provider_services[service_name]
    config_obj = _resolve_config(cloud_provider, config)
    # exclude_none so callers who pass {"region_name": None} share a cache
    # entry with callers who omit the key entirely.
    config_dict = config_obj.model_dump(exclude_none=True)

    return ClientCache().get_or_create(  # type: ignore[no-any-return]
        cloud_provider,
        service_name,
        config_dict,
        lambda _: service_class(config_obj),
    )
