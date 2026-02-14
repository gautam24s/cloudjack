"""AWS EC2 implementation of the Compute blueprint."""

from __future__ import annotations

from typing import Any, NoReturn

import boto3
from botocore.exceptions import ClientError

from cloud.base.compute import ComputeBlueprint
from cloud.base.exceptions import (
    ComputeError,
    InstanceNotFoundError,
)

_ERROR_MAP: dict[str, type[ComputeError]] = {
    "InvalidInstanceID.NotFound": InstanceNotFoundError,
    "InvalidInstanceID.Malformed": InstanceNotFoundError,
}


def _handle(e: ClientError, msg: str) -> NoReturn:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or ComputeError)(msg) from e


class Compute(ComputeBlueprint):
    """AWS EC2 compute service.

    Attributes:
        client: boto3 EC2 client.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the EC2 client.

        Args:
            config: AWS credentials dict (``aws_access_key_id``,
                ``aws_secret_access_key``, ``region_name``).
        """
        self.client = boto3.client(
            "ec2",
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            region_name=config.get("region_name"),
        )

    def create_instance(
        self,
        name: str,
        instance_type: str,
        image_id: str,
        **kwargs: Any,
    ) -> str:
        """Launch an EC2 instance.

        Supported kwargs:
            key_name, security_group_ids, subnet_id, user_data, min_count, max_count.

        Returns:
            Instance ID.
        """
        try:
            params: dict[str, Any] = {
                "ImageId": image_id,
                "InstanceType": instance_type,
                "MinCount": kwargs.get("min_count", 1),
                "MaxCount": kwargs.get("max_count", 1),
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": name}],
                    }
                ],
            }
            if "key_name" in kwargs:
                params["KeyName"] = kwargs["key_name"]
            if "security_group_ids" in kwargs:
                params["SecurityGroupIds"] = kwargs["security_group_ids"]
            if "subnet_id" in kwargs:
                params["SubnetId"] = kwargs["subnet_id"]
            if "user_data" in kwargs:
                params["UserData"] = kwargs["user_data"]
            resp = self.client.run_instances(**params)
            return resp["Instances"][0]["InstanceId"]  # type: ignore[no-any-return]
        except ClientError as e:
            _handle(e, f"Failed to create instance '{name}'")

    def start_instance(self, instance_id: str) -> None:
        """Start a stopped EC2 instance.

        Args:
            instance_id: EC2 instance ID (e.g. ``i-0abcd1234``).

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            self.client.start_instances(InstanceIds=[instance_id])
        except ClientError as e:
            _handle(e, f"Failed to start instance '{instance_id}'")

    def stop_instance(self, instance_id: str) -> None:
        """Stop a running EC2 instance (preserves EBS volumes).

        Args:
            instance_id: EC2 instance ID.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            self.client.stop_instances(InstanceIds=[instance_id])
        except ClientError as e:
            _handle(e, f"Failed to stop instance '{instance_id}'")

    def terminate_instance(self, instance_id: str) -> None:
        """Terminate an EC2 instance permanently.

        Args:
            instance_id: EC2 instance ID.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            self.client.terminate_instances(InstanceIds=[instance_id])
        except ClientError as e:
            _handle(e, f"Failed to terminate instance '{instance_id}'")

    def list_instances(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List EC2 instances.

        Args:
            **kwargs: ``filters`` — list of EC2 API filter dicts.

        Returns:
            List of dicts with ``instance_id``, ``name``, ``state``,
            ``instance_type``, ``launch_time``.

        Raises:
            ComputeError: On EC2 API failure.
        """
        try:
            params: dict[str, Any] = {}
            if "filters" in kwargs:
                params["Filters"] = kwargs["filters"]
            resp = self.client.describe_instances(**params)
            instances: list[dict[str, Any]] = []
            for reservation in resp.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    name = ""
                    for tag in inst.get("Tags", []):
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                            break
                    instances.append(
                        {
                            "instance_id": inst["InstanceId"],
                            "name": name,
                            "state": inst["State"]["Name"],
                            "instance_type": inst.get("InstanceType"),
                            "launch_time": str(inst.get("LaunchTime", "")),
                        }
                    )
            return instances
        except ClientError as e:
            _handle(e, "Failed to list instances")

    def get_instance(self, instance_id: str) -> dict[str, Any]:
        """Get details for a single EC2 instance.

        Args:
            instance_id: EC2 instance ID.

        Returns:
            Dict with ``instance_id``, ``name``, ``state``,
            ``instance_type``, ``launch_time``, ``public_ip``,
            ``private_ip``.

        Raises:
            InstanceNotFoundError: If the instance does not exist.
        """
        try:
            resp = self.client.describe_instances(InstanceIds=[instance_id])
            inst = resp["Reservations"][0]["Instances"][0]
            name = ""
            for tag in inst.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break
            return {
                "instance_id": inst["InstanceId"],
                "name": name,
                "state": inst["State"]["Name"],
                "instance_type": inst.get("InstanceType"),
                "launch_time": str(inst.get("LaunchTime", "")),
                "public_ip": inst.get("PublicIpAddress"),
                "private_ip": inst.get("PrivateIpAddress"),
            }
        except ClientError as e:
            _handle(e, f"Failed to get instance '{instance_id}'")
