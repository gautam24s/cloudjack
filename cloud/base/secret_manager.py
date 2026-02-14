"""Secret Manager service blueprint."""

from abc import ABC, abstractmethod


class SecretManagerBlueprint(ABC):
    """Abstract interface for secret management services.

    Maps to AWS Secrets Manager and GCP Secret Manager.
    """

    @abstractmethod
    def get_secret(self, name: str) -> str:
        """Retrieve a secret value by name.

        Args:
            name: Secret name or identifier.

        Returns:
            The secret value as a string.
        """
        pass

    @abstractmethod
    def create_secret(self, name: str, value: str) -> None:
        """Create a new secret.

        Args:
            name: Secret name.
            value: Secret value.
        """
        pass

    @abstractmethod
    def update_secret(self, name: str, value: str) -> None:
        """Update an existing secret's value.

        Args:
            name: Secret name.
            value: New secret value.
        """
        pass

    @abstractmethod
    def delete_secret(self, name: str) -> None:
        """Delete a secret by name.

        Args:
            name: Secret name.
        """
        pass
