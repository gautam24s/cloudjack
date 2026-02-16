"""IAM / Auth service blueprint."""

from abc import ABC, abstractmethod
from typing import Any


class IAMBlueprint(ABC):
    """Abstract interface for identity and access management.

    Maps to AWS IAM and GCP IAM.
    """

    # --- Role management ---

    @abstractmethod
    def create_role(
        self,
        role_name: str,
        trust_policy: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """Create a role and return its ARN / identifier.

        Args:
            role_name: Name of the role.
            trust_policy: Trust / assume-role policy document.
                For **AWS**, this is a standard IAM assume-role policy JSON.
                For **GCP**, this is a dict with ``title``, ``description``,
                ``permissions`` (list of strings), and optional
                ``stage`` (default ``GA``).

        Keyword Args:
            description (str): Role description *(AWS)*.
            max_session_duration (int): Max session duration
                in seconds *(AWS)*.

        Returns:
            Role identifier (ARN for AWS, full name for GCP).
        """

    @abstractmethod
    def delete_role(self, role_name: str) -> None:
        """Delete a role by name."""

    @abstractmethod
    def list_roles(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List roles.

        Each dict contains at least ``role_name`` and ``role_id``.

        Keyword Args:
            path_prefix (str): Filter roles by IAM path prefix *(AWS)*.
            parent (str): Override the default project scope *(GCP)*.
        """

    # --- Policy management ---

    @abstractmethod
    def attach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Attach a managed policy to a role.

        Args:
            role_name: Target role.
            policy_identifier: Policy name or member to attach.
                For **AWS**, pass a policy name (e.g. ``ReadOnlyAccess``
                or ``MyCustomPolicy``). The full ARN is constructed
                automatically. Pass ``managed=True`` for AWS-managed
                policies. Full ARNs (``arn:aws:...``) are also accepted.
                For **GCP**, pass a member string
                (e.g. ``user:alice@example.com``).

        Keyword Args:
            managed (bool): If ``True``, treat as an AWS-managed
                policy, default ``False`` *(AWS)*.
        """

    @abstractmethod
    def detach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Detach a managed policy from a role.

        Args:
            role_name: Target role.
            policy_identifier: Policy name or member to detach.
                For **AWS**, pass a policy name. The full ARN is constructed
                automatically. Pass ``managed=True`` for AWS-managed
                policies. Full ARNs are also accepted.
                For **GCP**, pass a member string.

        Keyword Args:
            managed (bool): If ``True``, treat as an AWS-managed
                policy, default ``False`` *(AWS)*.
        """

    @abstractmethod
    def list_policies(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List available managed policies.

        Each dict contains at least ``policy_name`` and ``policy_identifier``.

        Keyword Args:
            scope (str): Policy scope, default ``Local`` *(AWS)*.
            path_prefix (str): Filter by IAM path prefix *(AWS)*.
        """
