"""AWS IAM implementation of the IAM blueprint."""

from __future__ import annotations

import json
from typing import Any, NoReturn

import boto3
from botocore.exceptions import ClientError

from cloud.base.iam import IAMBlueprint
from cloud.base.exceptions import (
    IAMError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PolicyNotFoundError,
)
from cloud.base.config import AWSConfig

_ERROR_MAP: dict[str, type[IAMError]] = {
    "NoSuchEntity": RoleNotFoundError,
    "EntityAlreadyExists": RoleAlreadyExistsError,
    "DeleteConflict": IAMError,
}


def _handle(e: ClientError, msg: str) -> NoReturn:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or IAMError)(msg) from e


class IAM(IAMBlueprint):
    """AWS IAM service.

    Attributes:
        client: boto3 IAM client.
    """

    def __init__(self, config: AWSConfig) -> None:
        """Initialize the IAM client.

        Args:
            config: AWS configuration object containing credentials and region.
                   Expected attributes:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "iam",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )
        sts = boto3.client(
            "sts",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )
        self.account_id: str = sts.get_caller_identity()["Account"]

    def _build_policy_arn(self, policy_name: str, **kwargs: Any) -> str:
        """Construct a full IAM policy ARN from a policy name.

        Args:
            policy_name: Short policy name (e.g. ``ReadOnlyAccess``,
                ``MyCustomPolicy``). If it already looks like an ARN
                (starts with ``arn:``), it is returned as-is.
            **kwargs:
                managed: If ``True``, treat as an AWS-managed policy
                    (account = ``aws``). Default ``False`` (customer-managed,
                    uses ``self.account_id``).

        Returns:
            Full policy ARN string.
        """
        if policy_name.startswith("arn:"):
            return policy_name
        account = "aws" if kwargs.get("managed") else self.account_id
        return f"arn:aws:iam::{account}:policy/{policy_name}"

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
            return resp["Role"]["Arn"]  # type: ignore[no-any-return]
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
            roles: list[dict[str, Any]] = []
            paginator = self.client.get_paginator("list_roles")
            for page in paginator.paginate(**params):
                roles.extend(
                    {
                        "role_name": r["RoleName"],
                        "role_id": r["RoleId"],
                        "arn": r["Arn"],
                        "create_date": str(r.get("CreateDate", "")),
                    }
                    for r in page.get("Roles", [])
                )
            return roles
        except ClientError as e:
            _handle(e, "Failed to list roles")

    # --- Policy management ---

    def attach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Attach a managed policy to an IAM role.

        Args:
            role_name: Target role name.
            policy_identifier: Policy name (e.g. ``ReadOnlyAccess``).
                The full ARN is constructed automatically.
            **kwargs:
                managed: If ``True``, treat as an AWS-managed policy.
                    Default ``False`` (customer-managed).

        Raises:
            RoleNotFoundError: If the role does not exist.
            PolicyNotFoundError: If the policy does not exist.
        """
        try:
            arn = self._build_policy_arn(policy_identifier, **kwargs)
            self.client.attach_role_policy(
                RoleName=role_name, PolicyArn=arn
            )
        except ClientError as e:
            _handle(e, f"Failed to attach policy '{policy_identifier}' to role '{role_name}'")

    def detach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Detach a managed policy from an IAM role.

        Args:
            role_name: Target role name.
            policy_identifier: Policy name (e.g. ``ReadOnlyAccess``).
                The full ARN is constructed automatically.
            **kwargs:
                managed: If ``True``, treat as an AWS-managed policy.
                    Default ``False`` (customer-managed).

        Raises:
            RoleNotFoundError: If the role does not exist.
        """
        try:
            arn = self._build_policy_arn(policy_identifier, **kwargs)
            self.client.detach_role_policy(
                RoleName=role_name, PolicyArn=arn
            )
        except ClientError as e:
            _handle(e, f"Failed to detach policy '{policy_identifier}' from role '{role_name}'")

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
            policies: list[dict[str, Any]] = []
            paginator = self.client.get_paginator("list_policies")
            for page in paginator.paginate(**params):
                policies.extend(
                    {
                        "policy_name": p["PolicyName"],
                        "policy_identifier": p["Arn"],
                        "create_date": str(p.get("CreateDate", "")),
                    }
                    for p in page.get("Policies", [])
                )
            return policies
        except ClientError as e:
            _handle(e, "Failed to list policies")
