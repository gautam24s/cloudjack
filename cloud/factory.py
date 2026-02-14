"""
Universal Factory
"""

from typing import overload, Literal, Any

from cloud.base import SecretManagerBlueprint, CloudStorageBlueprint
from cloud.aws.factory import SERVICE_REGISTRY as AWS_SERVICES
from cloud.gcp.factory import SERVICE_REGISTRY as GCP_SERVICES


# Nested factory registry: cloud_provider -> service registry
_FACTORY_REGISTRY: dict[str, dict[str, type]] = {
    "aws": AWS_SERVICES,
    "gcp": GCP_SERVICES,
}


@overload
def universal_factory(
    service_name: Literal["secret_manager"], cloud_provider: Literal["aws"], config: dict
) -> SecretManagerBlueprint: ...


@overload
def universal_factory(
    service_name: Literal["storage"], cloud_provider: str, config: dict
) -> CloudStorageBlueprint: ...


def universal_factory(
    service_name: str, cloud_provider: str, config: dict
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
        raise ValueError(f"Unsupported service '{service_name}' for provider '{cloud_provider}'")
    
    service_class = provider_services[service_name]
    return service_class(config)
