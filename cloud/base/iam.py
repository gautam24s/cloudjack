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
            **kwargs: Provider-specific options (description, tags, …).

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
        """

    # --- Policy management ---

    @abstractmethod
    def attach_policy(self, role_name: str, policy_arn: str) -> None:
        """Attach a managed policy to a role.

        Args:
            role_name: Target role.
            policy_arn: Policy ARN or identifier to attach.
        """

    @abstractmethod
    def detach_policy(self, role_name: str, policy_arn: str) -> None:
        """Detach a managed policy from a role."""

    @abstractmethod
    def list_policies(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List available managed policies.

        Each dict contains at least ``policy_name`` and ``policy_arn``.
        """
