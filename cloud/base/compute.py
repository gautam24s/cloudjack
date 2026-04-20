"""Compute (VM) service blueprint."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from cloud.base.types import InstanceDict


class ComputeService(ABC):
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

        Keyword Args:
            key_name (str): EC2 key pair name for SSH access *(AWS)*.
            security_group_ids (list[str]): List of security group IDs *(AWS)*.
            subnet_id (str): VPC subnet ID *(AWS)*.
            user_data (str): Instance bootstrap script *(AWS)*.
            min_count (int): Minimum instances to launch, default ``1`` *(AWS)*.
            max_count (int): Maximum instances to launch, default ``1`` *(AWS)*.
            zone (str): Compute zone, e.g. ``us-central1-a`` *(GCP)*.
            network (str): Network name, default
                ``global/networks/default`` *(GCP)*.
            subnet (str): Subnetwork name *(GCP)*.
            preemptible (bool): Whether to use a preemptible VM *(GCP)*.
            service_account_email (str): Service account for the VM *(GCP)*.
            metadata (dict): Dict of instance metadata key-value pairs *(GCP)*.

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
    def list_instances(self, **kwargs: Any) -> list[InstanceDict]:
        """List instances.

        Each dict contains at least:
            - ``instance_id``
            - ``name``
            - ``state`` (running / stopped / terminated / …)

        Keyword Args:
            filters (list[dict]): List of EC2 API filter dicts, e.g.
                ``[{"Name": "instance-state-name", "Values": ["running"]}]``
                *(AWS)*.
            zone (str): Compute zone to list instances from *(GCP)*.
            filter (str): GCP API filter string *(GCP)*.
        """

    @abstractmethod
    def get_instance(self, instance_id: str) -> InstanceDict:
        """Return details for a single instance.

        Returns:
            Dict with ``instance_id``, ``name``, ``state``, ``instance_type``,
            ``launch_time``, and provider-specific extras.
        """

    # --- Async variants ---

    async def acreate_instance(
        self,
        name: str,
        instance_type: str,
        image_id: str,
        **kwargs: Any,
    ) -> str:
        """Async variant of :meth:`create_instance` (runs in a worker thread)."""
        return await asyncio.to_thread(
            self.create_instance, name, instance_type, image_id, **kwargs
        )

    async def astart_instance(self, instance_id: str) -> None:
        """Async variant of :meth:`start_instance` (runs in a worker thread)."""
        return await asyncio.to_thread(self.start_instance, instance_id)

    async def astop_instance(self, instance_id: str) -> None:
        """Async variant of :meth:`stop_instance` (runs in a worker thread)."""
        return await asyncio.to_thread(self.stop_instance, instance_id)

    async def aterminate_instance(self, instance_id: str) -> None:
        """Async variant of :meth:`terminate_instance` (runs in a worker thread)."""
        return await asyncio.to_thread(self.terminate_instance, instance_id)

    async def alist_instances(self, **kwargs: Any) -> list[InstanceDict]:
        """Async variant of :meth:`list_instances` (runs in a worker thread)."""
        return await asyncio.to_thread(self.list_instances, **kwargs)

    async def aget_instance(self, instance_id: str) -> InstanceDict:
        """Async variant of :meth:`get_instance` (runs in a worker thread)."""
        return await asyncio.to_thread(self.get_instance, instance_id)
