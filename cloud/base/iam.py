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

                - **AWS**: Standard IAM assume-role policy JSON.
                - **GCP**: Dict with ``title``, ``description``,
                  ``permissions`` (list of strings), and optional
                  ``stage`` (default ``GA``).

            **kwargs: Provider-specific options:

                **AWS (IAM):**
                    - ``description``: Role description.
                    - ``max_session_duration``: Max session duration in seconds.

                **GCP (IAM Admin):**
                    *(options encoded in trust_policy dict)*

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

        Args:
            **kwargs: Provider-specific filters:

                **AWS (IAM):**
                    - ``path_prefix``: Filter roles by IAM path prefix.

                **GCP (IAM Admin):**
                    - ``parent``: Override the default project scope.
        """

    # --- Policy management ---

    @abstractmethod
    def attach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Attach a managed policy to a role.

        Args:
            role_name: Target role.
            policy_identifier: Policy name or member to attach.

                - **AWS**: Policy name (e.g. ``ReadOnlyAccess`` or
                  ``MyCustomPolicy``). The full ARN is constructed
                  automatically. Pass ``managed=True`` for AWS-managed
                  policies. Full ARNs (``arn:aws:...``) are also accepted.
                - **GCP**: Member string (e.g. ``user:alice@example.com``).

            **kwargs: Provider-specific options:

                **AWS (IAM):**
                    - ``managed``: If ``True``, treat as an AWS-managed
                      policy (default ``False``).

                **GCP (IAM Admin):**
                    *(no additional kwargs)*
        """

    @abstractmethod
    def detach_policy(self, role_name: str, policy_identifier: str, **kwargs: Any) -> None:
        """Detach a managed policy from a role.

        Args:
            role_name: Target role.
            policy_identifier: Policy name or member to detach.

                - **AWS**: Policy name. The full ARN is constructed
                  automatically. Pass ``managed=True`` for AWS-managed
                  policies. Full ARNs are also accepted.
                - **GCP**: Member string.

            **kwargs: Provider-specific options:

                **AWS (IAM):**
                    - ``managed``: If ``True``, treat as an AWS-managed
                      policy (default ``False``).

                **GCP (IAM Admin):**
                    *(no additional kwargs)*
        """

    @abstractmethod
    def list_policies(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List available managed policies.

        Each dict contains at least ``policy_name`` and ``policy_identifier``.

        Args:
            **kwargs: Provider-specific filters:

                **AWS (IAM):**
                    - ``scope``: Policy scope (default ``Local``).
                    - ``path_prefix``: Filter by IAM path prefix.

                **GCP (IAM Admin):**
                    *(returns project-level IAM bindings, no additional kwargs)*
        """
