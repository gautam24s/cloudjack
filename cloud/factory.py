"""Universal service factory.

Provides :func:`universal_factory`, the single entry-point for creating
cloud service clients.  The function dispatches to provider-specific
factories (AWS, GCP) based on ``cloud_provider`` and returns a typed
instance via ``@overload`` signatures so IDEs can autocomplete methods.
"""

from typing import overload, Literal, Any

from cloud.base import (
    SecretManagerBlueprint,
    CloudStorageBlueprint,
    QueueBlueprint,
    ComputeBlueprint,
    DNSBlueprint,
    IAMBlueprint,
    LoggingBlueprint,
    existing_services,
    existing_cloud_providers,
)
from cloud.base.config import validate_config
from cloud.aws.factory import SERVICE_REGISTRY as AWS_SERVICES
from cloud.gcp.factory import SERVICE_REGISTRY as GCP_SERVICES


# Nested factory registry: cloud_provider -> service registry
_FACTORY_REGISTRY: dict[str, dict[str, type]] = {
    "aws": AWS_SERVICES,
    "gcp": GCP_SERVICES,
}


@overload
def universal_factory(
    service_name: Literal["secret_manager"], cloud_provider: existing_cloud_providers, config: dict
) -> SecretManagerBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["storage"], cloud_provider: existing_cloud_providers, config: dict
) -> CloudStorageBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["queue"], cloud_provider: existing_cloud_providers, config: dict
) -> QueueBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["compute"], cloud_provider: existing_cloud_providers, config: dict
) -> ComputeBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["dns"], cloud_provider: existing_cloud_providers, config: dict
) -> DNSBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["iam"], cloud_provider: existing_cloud_providers, config: dict
) -> IAMBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["logging"], cloud_provider: existing_cloud_providers, config: dict
) -> LoggingBlueprint: ...


def universal_factory(
    service_name: existing_services,
    cloud_provider: existing_cloud_providers,
    config: dict,
) -> Any:
    """
    Universal factory function to create service instances based on cloud provider and service name.
    Args:
        service_name: The name of the service (e.g., 'secret_manager').
        cloud_provider: The cloud provider (e.g., 'aws', 'gcp').
        config: Configuration dictionary to initialize the service instance.
    Returns:
        An instance of the requested service class.
    Raises:
        ValueError: If the cloud provider or service is not supported.
    """
    if cloud_provider not in _FACTORY_REGISTRY:
        raise ValueError(f"Unsupported cloud provider: {cloud_provider}")

    provider_services = _FACTORY_REGISTRY[cloud_provider]

    if service_name not in provider_services:
        raise ValueError(
            f"Unsupported service '{service_name}' for provider '{cloud_provider}'"
        )

    service_class = provider_services[service_name]
    configObj = validate_config(cloud_provider, config)
    return service_class(configObj)
