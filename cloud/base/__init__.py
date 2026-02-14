"""Abstract service blueprints and core utilities.

Every cloud service inherits from one of the blueprints defined here.
Import them to type-hint your own code or to create custom providers.
"""

from .secret_manager import SecretManagerBlueprint
from .storage import CloudStorageBlueprint
from .queue import QueueBlueprint
from .compute import ComputeBlueprint
from .dns import DNSBlueprint
from .iam import IAMBlueprint
from .logging_service import LoggingBlueprint


__all__ = [
    "SecretManagerBlueprint",
    "CloudStorageBlueprint",
    "QueueBlueprint",
    "ComputeBlueprint",
    "DNSBlueprint",
    "IAMBlueprint",
    "LoggingBlueprint",
]
