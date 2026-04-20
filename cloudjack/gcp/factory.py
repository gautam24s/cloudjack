"""GCP service factory.

Maps service names to their GCP SDK implementations.
``SERVICE_REGISTRY`` is consumed by :func:`cloudjack.factory.universal_factory`.
"""

from cloudjack.gcp.secret_manager import SecretManager
from cloudjack.gcp.storage import Storage
from cloudjack.gcp.queue import Queue
from cloudjack.gcp.compute import Compute
from cloudjack.gcp.dns import DNS
from cloudjack.gcp.iam import IAM
from cloudjack.gcp.logging_service import Logging


# Service registry for GCP
SERVICE_REGISTRY: dict[str, type] = {
    "secret_manager": SecretManager,
    "storage": Storage,
    "queue": Queue,
    "compute": Compute,
    "dns": DNS,
    "iam": IAM,
    "logging": Logging,
}
