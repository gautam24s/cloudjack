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
            **kwargs: Provider-specific options (network, key pair, …).

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
            **kwargs: Provider-specific filters.
        """

    @abstractmethod
    def get_instance(self, instance_id: str) -> dict[str, Any]:
        """Return details for a single instance.

        Returns:
            Dict with ``instance_id``, ``name``, ``state``, ``instance_type``,
            ``launch_time``, and provider-specific extras.
        """
