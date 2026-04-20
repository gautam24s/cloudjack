"""AWS service factory.

Maps service names to their AWS SDK implementations.
``SERVICE_REGISTRY`` is consumed by :func:`cloudjack.factory.universal_factory`.
"""

from cloudjack.aws.secret_manager import SecretManager
from cloudjack.aws.storage import Storage
from cloudjack.aws.queue import Queue
from cloudjack.aws.compute import Compute
from cloudjack.aws.dns import DNS
from cloudjack.aws.iam import IAM
from cloudjack.aws.logging_service import Logging


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
