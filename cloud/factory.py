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
    CloudStorageBlueprint,
    ComputeBlueprint,
    DNSBlueprint,
    IAMBlueprint,
    LoggingBlueprint,
    QueueBlueprint,
    SecretManagerBlueprint,
    existing_cloud_providers,
    existing_services,
)
from cloud.base.client_cache import ClientCache
from cloud.base.config import validate_config


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


@overload
def universal_factory(
    service_name: Literal["secret_manager"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> SecretManagerBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["storage"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> CloudStorageBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["queue"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> QueueBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["compute"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> ComputeBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["dns"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> DNSBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["iam"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> IAMBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["logging"],
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> LoggingBlueprint: ...


def universal_factory(
    service_name: existing_services,
    cloud_provider: existing_cloud_providers,
    config: dict | None = None,
) -> (
    SecretManagerBlueprint
    | CloudStorageBlueprint
    | QueueBlueprint
    | ComputeBlueprint
    | DNSBlueprint
    | IAMBlueprint
    | LoggingBlueprint
):
    """Create a cloud service client.

    The matching provider module is imported on demand, so projects that
    only install one extra (``cloudjack[aws]`` or ``cloudjack[gcp]``) do
    not need the other provider's SDK to be present.

    Args:
        service_name: Service identifier (``secret_manager``, ``storage``,
            ``queue``, ``compute``, ``dns``, ``iam``, ``logging``).
        cloud_provider: Cloud provider (``aws`` or ``gcp``).
        config: Optional configuration dict. Missing fields fall back to
            environment variables and the provider SDK's default credential
            chain; see :class:`cloud.base.config.AWSConfig` /
            :class:`cloud.base.config.GCPConfig`.

    Returns:
        A cached service instance conforming to the matching blueprint.

    Raises:
        ValueError: If the cloud provider or service is not supported.
        ImportError: If the provider's optional dependencies are missing.
            Install with ``pip install 'cloudjack[<provider>]'``.
    """
    provider_services = _load_service_registry(cloud_provider)

    if service_name not in provider_services:
        raise ValueError(
            f"Unsupported service '{service_name}' for provider '{cloud_provider}'"
        )

    service_class = provider_services[service_name]
    config_obj = validate_config(cloud_provider, config)
    # exclude_none so callers who pass {"region_name": None} share a cache
    # entry with callers who omit the key entirely.
    config_dict = config_obj.model_dump(exclude_none=True)

    return ClientCache().get_or_create(  # type: ignore[no-any-return]
        cloud_provider,
        service_name,
        config_dict,
        lambda _: service_class(config_obj),
    )
