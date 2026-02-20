"""GCP Compute Engine implementation of the Compute blueprint."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exceptions
from google.cloud import compute_v1

from cloud.base.compute import ComputeBlueprint
from cloud.base.config import GCPConfig
from cloud.base.exceptions import ComputeError, InstanceNotFoundError, InstanceAlreadyExistsError


class Compute(ComputeBlueprint):
    """GCP Compute Engine service.

    Attributes:
        project_id: GCP project ID.
        zone: Default zone for instance operations.
        client: Compute Engine instances client.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize the Compute Engine client.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        assert config.project_id is not None  # guaranteed by GCPConfig validator
        self.project_id: str = config.project_id
        self.zone: str = "us-central1-a"
        self.client = compute_v1.InstancesClient(credentials=config.credentials)
        self._zone_ops = compute_v1.ZoneOperationsClient(credentials=config.credentials)

    def _wait(self, operation: Any) -> None:
        """Block until a zone operation completes."""
        self._zone_ops.wait(
            project=self.project_id,
            zone=self.zone,
            operation=operation.name,
        )

    def create_instance(
        self,
        name: str,
        instance_type: str,
        image_id: str,
        **kwargs: Any,
    ) -> str:
        """Launch a Compute Engine instance.

        Args:
            name: Instance name.
            instance_type: Machine type (e.g. ``e2-micro``).
            image_id: Source image URL or family
                      (e.g. ``projects/debian-cloud/global/images/family/debian-12``).
            **kwargs: ``zone``, ``network``, ``subnet``, ``disk_size_gb``.

        Returns:
            Instance name (GCE uses name as identifier).
        """
        zone = kwargs.get("zone", self.zone)
        try:
            instance = compute_v1.Instance()
            instance.name = name
            instance.machine_type = (
                f"zones/{zone}/machineTypes/{instance_type}"
            )
            disk = compute_v1.AttachedDisk()
            disk.auto_delete = True
            disk.boot = True
            init = compute_v1.AttachedDiskInitializeParams()
            init.source_image = image_id
            init.disk_size_gb = kwargs.get("disk_size_gb", 10)
            disk.initialize_params = init
            instance.disks = [disk]

            network_interface = compute_v1.NetworkInterface()
            network_interface.network = kwargs.get(
                "network", "global/networks/default"
            )
            instance.network_interfaces = [network_interface]

            op = self.client.insert(
                project=self.project_id, zone=zone, instance_resource=instance
            )
            self._wait(op)
            return name
        except gcp_exceptions.AlreadyExists as e:
            raise InstanceAlreadyExistsError(
                f"Instance '{name}' already exists"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError(f"Failed to create instance '{name}'") from e

    def start_instance(self, instance_id: str) -> None:
        """Start a stopped Compute Engine instance.

        Args:
            instance_id: Instance name.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            op = self.client.start(
                project=self.project_id, zone=self.zone, instance=instance_id
            )
            self._wait(op)
        except gcp_exceptions.NotFound as e:
            raise InstanceNotFoundError(
                f"Instance '{instance_id}' not found"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError(f"Failed to start '{instance_id}'") from e

    def stop_instance(self, instance_id: str) -> None:
        """Stop a running Compute Engine instance.

        Args:
            instance_id: Instance name.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            op = self.client.stop(
                project=self.project_id, zone=self.zone, instance=instance_id
            )
            self._wait(op)
        except gcp_exceptions.NotFound as e:
            raise InstanceNotFoundError(
                f"Instance '{instance_id}' not found"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError(f"Failed to stop '{instance_id}'") from e

    def terminate_instance(self, instance_id: str) -> None:
        """Delete (terminate) a Compute Engine instance.

        Args:
            instance_id: Instance name.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            op = self.client.delete(
                project=self.project_id, zone=self.zone, instance=instance_id
            )
            self._wait(op)
        except gcp_exceptions.NotFound as e:
            raise InstanceNotFoundError(
                f"Instance '{instance_id}' not found"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError(f"Failed to terminate '{instance_id}'") from e

    def list_instances(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List Compute Engine instances in a zone.

        Args:
            **kwargs: ``zone`` — override the default zone.

        Returns:
            List of dicts with ``instance_id``, ``name``, ``state``,
            ``instance_type``, ``launch_time``.

        Raises:
            ComputeError: On Compute Engine API failure.
        """
        try:
            zone = kwargs.get("zone", self.zone)
            instances = self.client.list(project=self.project_id, zone=zone)
            return [
                {
                    "instance_id": inst.name,
                    "name": inst.name,
                    "state": inst.status,
                    "instance_type": inst.machine_type.split("/")[-1]
                    if inst.machine_type
                    else "",
                    "launch_time": str(inst.creation_timestamp or ""),
                }
                for inst in instances
            ]
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError("Failed to list instances") from e

    def get_instance(self, instance_id: str) -> dict[str, Any]:
        """Get details for a single Compute Engine instance.

        Args:
            instance_id: Instance name.

        Returns:
            Dict with ``instance_id``, ``name``, ``state``,
            ``instance_type``, ``launch_time``, ``public_ip``,
            ``private_ip``.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            inst = self.client.get(
                project=self.project_id, zone=self.zone, instance=instance_id
            )
            ips = []
            for iface in (inst.network_interfaces or []):
                for ac in (iface.access_configs or []):
                    if ac.nat_i_p:
                        ips.append(ac.nat_i_p)
            return {
                "instance_id": inst.name,
                "name": inst.name,
                "state": inst.status,
                "instance_type": inst.machine_type.split("/")[-1]
                if inst.machine_type
                else "",
                "launch_time": str(inst.creation_timestamp or ""),
                "public_ip": ips[0] if ips else None,
                "private_ip": (
                    inst.network_interfaces[0].network_i_p
                    if inst.network_interfaces
                    else None
                ),
            }
        except gcp_exceptions.NotFound as e:
            raise InstanceNotFoundError(
                f"Instance '{instance_id}' not found"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise ComputeError(f"Failed to get instance '{instance_id}'") from e
