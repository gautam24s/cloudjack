"""AWS service factory.

Maps service names to their AWS SDK implementations.
``SERVICE_REGISTRY`` is consumed by :func:`cloud.factory.universal_factory`.
"""

from cloud.aws.secret_manager import SecretManager
from cloud.aws.storage import Storage
from cloud.aws.queue import Queue
from cloud.aws.compute import Compute
from cloud.aws.dns import DNS
from cloud.aws.iam import IAM
from cloud.aws.logging_service import Logging


# Service registry for AWS
SERVICE_REGISTRY: dict[str, type] = {
    "secret_manager": SecretManager,
    "storage": Storage,
    "queue": Queue,
    "compute": Compute,
    "dns": DNS,
    "iam": IAM,
    "logging": Logging,
}
