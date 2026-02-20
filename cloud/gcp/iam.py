"""GCP IAM implementation of the IAM blueprint."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exceptions
from google.cloud import iam_admin_v1
from google.iam.v1 import iam_policy_pb2  # noqa: F401 — used by the client

from cloud.base.iam import IAMBlueprint
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    IAMError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
)


class IAM(IAMBlueprint):
    """GCP IAM service.

    Uses the IAM Admin API for custom role management and
    the Resource Manager API for policy bindings.

    Attributes:
        project_id: GCP project ID.
        client: IAM Admin client.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize the IAM Admin client.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        self.project_id: str = config.project_id
        self.client = iam_admin_v1.IAMClient()

    # --- Role management ---

    def create_role(
        self,
        role_name: str,
        trust_policy: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """Create a GCP custom role.

        The *trust_policy* dict is interpreted as:
            - ``title``: Role display title.
            - ``description``: Role description.
            - ``permissions``: List of permission strings.
            - ``stage``: Launch stage (default ``GA``).

        Returns:
            Full role name (``projects/<project>/roles/<role>``).
        """
        try:
            role = iam_admin_v1.Role()
            role.title = trust_policy.get("title", role_name)
            role.description = trust_policy.get("description", "")
            role.included_permissions = trust_policy.get("permissions", [])
            role.stage = getattr(
                iam_admin_v1.Role.RoleLaunchStage,
                trust_policy.get("stage", "GA"),
                iam_admin_v1.Role.RoleLaunchStage.GA,  # type: ignore[arg-type]
            )
            resp = self.client.create_role(
                request={
                    "parent": f"projects/{self.project_id}",
                    "role_id": role_name,
                    "role": role,
                }
            )
            return resp.name
        except gcp_exceptions.AlreadyExists as e:
            raise RoleAlreadyExistsError(
                f"Role '{role_name}' already exists"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise IAMError(f"Failed to create role '{role_name}'") from e

    def delete_role(self, role_name: str) -> None:
        """Delete a GCP custom role.

        Args:
            role_name: Short role name or full resource path
                (e.g. ``projects/<project>/roles/<role>``).

        Raises:
            RoleNotFoundError: If the role does not exist.
        """
        try:
            full_name = (
                role_name
                if "/" in role_name
                else f"projects/{self.project_id}/roles/{role_name}"
            )
            self.client.delete_role(request={"name": full_name})
        except gcp_exceptions.NotFound as e:
            raise RoleNotFoundError(f"Role '{role_name}' not found") from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise IAMError(f"Failed to delete role '{role_name}'") from e

    def list_roles(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List GCP custom roles.

        Args:
            **kwargs: ``parent`` — override the default project scope.

        Returns:
            List of dicts with ``role_name``, ``role_id``, ``title``,
            ``description``.

        Raises:
            IAMError: On IAM API failure.
        """
        try:
            parent = kwargs.get("parent", f"projects/{self.project_id}")
            roles = self.client.list_roles(request={"parent": parent})
            return [
                {
                    "role_name": r.name.split("/")[-1],
                    "role_id": r.name,
                    "title": r.title,
                    "description": r.description,
                }
                for r in roles
            ]
        except gcp_exceptions.GoogleAPICallError as e:
            raise IAMError("Failed to list roles") from e

    # --- Policy management ---
    # GCP IAM binds roles to members via project-level IAM policies.
    # attach_policy / detach_policy add / remove a binding entry.

    def _get_policy(self) -> Any:
        """Fetch the project-level IAM policy via Resource Manager."""
        from google.cloud import resourcemanager_v3

        rm = resourcemanager_v3.ProjectsClient()
        return rm.get_iam_policy(
            request={"resource": f"projects/{self.project_id}"}
        )

    def _set_policy(self, policy: Any) -> None:
        """Write back the project-level IAM policy via Resource Manager."""
        from google.cloud import resourcemanager_v3

        rm = resourcemanager_v3.ProjectsClient()
        rm.set_iam_policy(
            request={
                "resource": f"projects/{self.project_id}",
                "policy": policy,
            }
        )

    def attach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Attach a role binding for a member.

        Args:
            role_name: Full GCP role name (e.g. ``roles/viewer``
                       or ``projects/<p>/roles/<r>``).
            policy_identifier: Member string (e.g. ``user:alice@example.com``).
        """
        try:
            policy = self._get_policy()
            for binding in policy.bindings:
                if binding.role == role_name:
                    if policy_identifier not in binding.members:
                        binding.members.append(policy_identifier)
                    self._set_policy(policy)
                    return
            # No existing binding for this role → create one
            from google.iam.v1 import policy_pb2

            new_binding = policy_pb2.Binding()
            new_binding.role = role_name
            new_binding.members.append(policy_identifier)
            policy.bindings.append(new_binding)
            self._set_policy(policy)
        except Exception as e:
            raise IAMError(
                f"Failed to attach '{policy_identifier}' to '{role_name}'"
            ) from e

    def detach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Remove a member from a role binding in the project IAM policy.

        Args:
            role_name: GCP role (e.g. ``roles/viewer``).
            policy_identifier: Member string (e.g. ``user:alice@example.com``).

        Raises:
            IAMError: On API failure.
        """
        try:
            policy = self._get_policy()
            for binding in policy.bindings:
                if binding.role == role_name and policy_identifier in binding.members:
                    binding.members.remove(policy_identifier)
                    break
            self._set_policy(policy)
        except Exception as e:
            raise IAMError(
                f"Failed to detach '{policy_identifier}' from '{role_name}'"
            ) from e

    def list_policies(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List GCP IAM policy bindings for the project.

        Returns:
            One dict per binding with ``policy_name`` (role) and
            ``policy_identifier`` (role identifier).
        """
        try:
            policy = self._get_policy()
            return [
                {
                    "policy_name": b.role,
                    "policy_identifier": b.role,
                    "members": list(b.members),
                }
                for b in policy.bindings
            ]
        except Exception as e:
            raise IAMError("Failed to list policies") from e
