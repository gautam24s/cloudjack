"""Cloudjack — unified multi-cloud SDK for AWS and GCP.

Entry point for the library. Import :func:`universal_factory` to create
any service client with a single call::

    from cloud import universal_factory

    storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})
"""

from .base import (
    SecretManagerBlueprint,
    CloudStorageBlueprint,
    QueueBlueprint,
    ComputeBlueprint,
    DNSBlueprint,
    IAMBlueprint,
    LoggingBlueprint,
)
from .factory import universal_factory

__all__ = [
    "SecretManagerBlueprint",
    "CloudStorageBlueprint",
    "QueueBlueprint",
    "ComputeBlueprint",
    "DNSBlueprint",
    "IAMBlueprint",
    "LoggingBlueprint",
    "universal_factory",
]