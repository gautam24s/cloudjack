"""
GCP Service Factory
"""

from cloud.gcp.secret_manager import SecretManager
from cloud.gcp.storage import Storage


# Service registry for GCP
SERVICE_REGISTRY: dict[str, type] = {
    "secret_manager": SecretManager,
    "storage": Storage,
}
