"""
AWS Service Factory
"""

from cloud.aws.secret_manager import SecretManager
from cloud.aws.storage import Storage


# Service registry for AWS
SERVICE_REGISTRY: dict[str, type] = {
    "secret_manager": SecretManager,
    "storage": Storage,
}
