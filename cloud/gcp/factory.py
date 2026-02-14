"""GCP service factory.

Maps service names to their GCP SDK implementations.
``SERVICE_REGISTRY`` is consumed by :func:`cloud.factory.universal_factory`.
"""

from cloud.gcp.secret_manager import SecretManager
from cloud.gcp.storage import Storage
from cloud.gcp.queue import Queue
from cloud.gcp.compute import Compute
from cloud.gcp.dns import DNS
from cloud.gcp.iam import IAM
from cloud.gcp.logging_service import Logging


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
