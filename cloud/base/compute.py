"""Compute (VM) service blueprint."""

from abc import ABC, abstractmethod
from typing import Any


class ComputeBlueprint(ABC):
    """Abstract interface for compute / virtual machine lifecycle.

    Maps to AWS EC2 and GCP Compute Engine.
    """

    @abstractmethod
    def create_instance(
        self,
        name: str,
        instance_type: str,
        image_id: str,
        **kwargs: Any,
    ) -> str:
        """Launch a new VM instance and return its ID.

        Args:
            name: Display name for the instance.
            instance_type: Machine type (e.g. ``t3.micro``, ``e2-micro``).
            image_id: OS image identifier (AMI ID / image family).
            **kwargs: Provider-specific options:

                **AWS (EC2):**
                    - ``key_name``: EC2 key pair name for SSH access.
                    - ``security_group_ids``: List of security group IDs.
                    - ``subnet_id``: VPC subnet ID.
                    - ``user_data``: Instance bootstrap script.
                    - ``min_count``: Minimum instances to launch (default 1).
                    - ``max_count``: Maximum instances to launch (default 1).

                **GCP (Compute Engine):**
                    - ``zone``: Compute zone (e.g. ``us-central1-a``).
                    - ``network``: Network name (default ``global/networks/default``).
                    - ``subnet``: Subnetwork name.
                    - ``preemptible``: Whether to use a preemptible VM.
                    - ``service_account_email``: Service account for the VM.
                    - ``metadata``: Dict of instance metadata key-value pairs.

        Returns:
            Instance ID.
        """

    @abstractmethod
    def start_instance(self, instance_id: str) -> None:
        """Start a stopped instance."""

    @abstractmethod
    def stop_instance(self, instance_id: str) -> None:
        """Stop a running instance (keep disk)."""

    @abstractmethod
    def terminate_instance(self, instance_id: str) -> None:
        """Terminate (destroy) an instance."""

    @abstractmethod
    def list_instances(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List instances.

        Each dict contains at least:
            - ``instance_id``
            - ``name``
            - ``state`` (running / stopped / terminated / …)

        Args:
            **kwargs: Provider-specific filters:

                **AWS (EC2):**
                    - ``filters``: List of EC2 API filter dicts
                      (e.g. ``[{"Name": "instance-state-name", "Values": ["running"]}]``).

                **GCP (Compute Engine):**
                    - ``zone``: Compute zone to list instances from.
                    - ``filter``: GCP API filter string.
        """

    @abstractmethod
    def get_instance(self, instance_id: str) -> dict[str, Any]:
        """Return details for a single instance.

        Returns:
            Dict with ``instance_id``, ``name``, ``state``, ``instance_type``,
            ``launch_time``, and provider-specific extras.
        """
