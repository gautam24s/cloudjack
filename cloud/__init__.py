"""Cloudjack — unified multi-cloud SDK for AWS and GCP.

Entry point for the library. Import :func:`universal_factory` to create
any service client with a single call::

    from cloud import universal_factory

    storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

The factory returns a concrete provider instance (e.g. an AWS S3 client
wrapper or a GCP Cloud Storage wrapper). The abstract service interfaces
those instances conform to are an internal implementation detail and are
intentionally not part of the public API — end users only work with the
factory and the resulting provider objects.
"""

from .base import (
    # Config — callers need these to type-check explicit config dicts
    AWSConfig,
    GCPConfig,
    # Utilities — safe to reuse from user code
    AsyncMixin,
    async_wrap,
    retry,
    # TypedDicts — describe values returned by service methods
    InstanceDict,
    LogEntryDict,
    MessageDict,
    PolicyDict,
    RecordDict,
    RoleDict,
    ZoneDict,
    # Exceptions — users need to catch these
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
from .factory import universal_factory

__all__ = [
    # Factory
    "universal_factory",
    # Config
    "AWSConfig",
    "GCPConfig",
    # Utilities
    "AsyncMixin",
    "async_wrap",
    "retry",
    # TypedDicts
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
