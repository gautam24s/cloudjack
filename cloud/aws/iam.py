"""AWS IAM implementation of the IAM blueprint."""

from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from cloud.base.iam import IAMBlueprint
from cloud.base.exceptions import (
    IAMError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PolicyNotFoundError,
)

_ERROR_MAP: dict[str, type[IAMError]] = {
    "NoSuchEntity": RoleNotFoundError,
    "EntityAlreadyExists": RoleAlreadyExistsError,
    "DeleteConflict": IAMError,
}


def _handle(e: ClientError, msg: str) -> None:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or IAMError)(msg) from e


class IAM(IAMBlueprint):
    """AWS IAM service.

    Attributes:
        client: boto3 IAM client.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the IAM client.

        Args:
            config: AWS credentials dict (``aws_access_key_id``,
                ``aws_secret_access_key``, ``region_name``).
        """
        self.client = boto3.client(
            "iam",
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            region_name=config.get("region_name"),
        )

    # --- Role management ---

    def create_role(
        self,
        role_name: str,
        trust_policy: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """Create an IAM role.

        Returns:
            Role ARN.
        """
        try:
            params: dict[str, Any] = {
                "RoleName": role_name,
                "AssumeRolePolicyDocument": json.dumps(trust_policy),
            }
            if "description" in kwargs:
                params["Description"] = kwargs["description"]
            if "max_session_duration" in kwargs:
                params["MaxSessionDuration"] = kwargs["max_session_duration"]
            resp = self.client.create_role(**params)
            return resp["Role"]["Arn"]
        except ClientError as e:
            _handle(e, f"Failed to create role '{role_name}'")

    def delete_role(self, role_name: str) -> None:
        """Delete an IAM role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            RoleNotFoundError: If the role does not exist.
        """
        try:
            self.client.delete_role(RoleName=role_name)
        except ClientError as e:
            _handle(e, f"Failed to delete role '{role_name}'")

    def list_roles(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List IAM roles.

        Args:
            **kwargs: ``path_prefix`` — filter roles by path.

        Returns:
            List of dicts with ``role_name``, ``role_id``, ``arn``,
            ``create_date``.

        Raises:
            IAMError: On IAM API failure.
        """
        try:
            params: dict[str, Any] = {}
            if "path_prefix" in kwargs:
                params["PathPrefix"] = kwargs["path_prefix"]
            resp = self.client.list_roles(**params)
            return [
                {
                    "role_name": r["RoleName"],
                    "role_id": r["RoleId"],
                    "arn": r["Arn"],
                    "create_date": str(r.get("CreateDate", "")),
                }
                for r in resp.get("Roles", [])
            ]
        except ClientError as e:
            _handle(e, "Failed to list roles")

    # --- Policy management ---

    def attach_policy(self, role_name: str, policy_arn: str) -> None:
        """Attach a managed policy to an IAM role.

        Args:
            role_name: Target role name.
            policy_arn: ARN of the policy to attach.

        Raises:
            RoleNotFoundError: If the role does not exist.
            PolicyNotFoundError: If the policy does not exist.
        """
        try:
            self.client.attach_role_policy(
                RoleName=role_name, PolicyArn=policy_arn
            )
        except ClientError as e:
            _handle(e, f"Failed to attach policy '{policy_arn}' to role '{role_name}'")

    def detach_policy(self, role_name: str, policy_arn: str) -> None:
        """Detach a managed policy from an IAM role.

        Args:
            role_name: Target role name.
            policy_arn: ARN of the policy to detach.

        Raises:
            RoleNotFoundError: If the role does not exist.
        """
        try:
            self.client.detach_role_policy(
                RoleName=role_name, PolicyArn=policy_arn
            )
        except ClientError as e:
            _handle(e, f"Failed to detach policy '{policy_arn}' from role '{role_name}'")

    def list_policies(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List IAM managed policies.

        Args:
            **kwargs: ``scope`` (default ``Local``), ``path_prefix``.

        Returns:
            List of dicts with ``policy_name``, ``policy_arn``,
            ``create_date``.

        Raises:
            IAMError: On IAM API failure.
        """
        try:
            params: dict[str, Any] = {
                "Scope": kwargs.get("scope", "Local"),
            }
            if "path_prefix" in kwargs:
                params["PathPrefix"] = kwargs["path_prefix"]
            resp = self.client.list_policies(**params)
            return [
                {
                    "policy_name": p["PolicyName"],
                    "policy_arn": p["Arn"],
                    "create_date": str(p.get("CreateDate", "")),
                }
                for p in resp.get("Policies", [])
            ]
        except ClientError as e:
            _handle(e, "Failed to list policies")
