from typing import Literal


existing_services = Literal[
    "secret_manager",
    "storage",
    "queue",
    "compute",
    "dns",
    "iam",
    "logging",
]


existing_cloud_providers = Literal["aws", "gcp"]
