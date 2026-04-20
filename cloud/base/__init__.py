"""Abstract service blueprints and core utilities.

Every cloud service inherits from one of the blueprints defined here.
Import them to type-hint your own code or to create custom providers.
"""

from .async_support import AsyncMixin, async_wrap
from .compute import ComputeBlueprint
from .config import AWSConfig, CONFIG_REGISTRY, GCPConfig, validate_config
from .dns import DNSBlueprint
from .exceptions import (
    BucketAlreadyExistsError,
    BucketNotFoundError,
    CloudjackError,
    ComputeError,
    DNSError,
    IAMError,
    InstanceAlreadyExistsError,
    InstanceNotFoundError,
    LogGroupAlreadyExistsError,
    LogGroupNotFoundError,
    LoggingError,
    MessageError,
    ObjectNotFoundError,
    PolicyNotFoundError,
    QueueAlreadyExistsError,
    QueueError,
    QueueNotFoundError,
    RecordNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    SecretAlreadyExistsError,
    SecretManagerError,
    SecretNotFoundError,
    StorageError,
    ZoneAlreadyExistsError,
    ZoneNotFoundError,
)
from .iam import IAMBlueprint
from .logging_service import LoggingBlueprint
from .queue import QueueBlueprint
from .retry import retry
from .secret_manager import SecretManagerBlueprint
from .storage import CloudStorageBlueprint
from .supported_services import existing_cloud_providers, existing_services
from .types import (
    InstanceDict,
    LogEntryDict,
    MessageDict,
    PolicyDict,
    RecordDict,
    RoleDict,
    ZoneDict,
)


__all__ = [
    # Blueprints
    "SecretManagerBlueprint",
    "CloudStorageBlueprint",
    "QueueBlueprint",
    "ComputeBlueprint",
    "DNSBlueprint",
    "IAMBlueprint",
    "LoggingBlueprint",
    # Service registry
    "existing_services",
    "existing_cloud_providers",
    # Config
    "AWSConfig",
    "GCPConfig",
    "CONFIG_REGISTRY",
    "validate_config",
    # Utilities
    "AsyncMixin",
    "async_wrap",
    "retry",
    # Return-shape TypedDicts
    "InstanceDict",
    "LogEntryDict",
    "MessageDict",
    "PolicyDict",
    "RecordDict",
    "RoleDict",
    "ZoneDict",
    # Exceptions
    "CloudjackError",
    "SecretManagerError",
    "SecretNotFoundError",
    "SecretAlreadyExistsError",
    "StorageError",
    "BucketNotFoundError",
    "BucketAlreadyExistsError",
    "ObjectNotFoundError",
    "QueueError",
    "QueueNotFoundError",
    "QueueAlreadyExistsError",
    "MessageError",
    "ComputeError",
    "InstanceNotFoundError",
    "InstanceAlreadyExistsError",
    "DNSError",
    "ZoneNotFoundError",
    "ZoneAlreadyExistsError",
    "RecordNotFoundError",
    "IAMError",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PolicyNotFoundError",
    "LoggingError",
    "LogGroupNotFoundError",
    "LogGroupAlreadyExistsError",
]
