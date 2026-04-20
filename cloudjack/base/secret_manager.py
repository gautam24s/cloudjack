"""Secret Manager service interface."""

import asyncio
from abc import ABC, abstractmethod


class SecretManagerService(ABC):
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

    @abstractmethod
    def create_secret(self, name: str, value: str) -> None:
        """Create a new secret.

        Args:
            name: Secret name.
            value: Secret value.
        """

    @abstractmethod
    def update_secret(self, name: str, value: str) -> None:
        """Update an existing secret's value.

        Args:
            name: Secret name.
            value: New secret value.
        """

    @abstractmethod
    def delete_secret(self, name: str) -> None:
        """Delete a secret by name.

        Args:
            name: Secret name.
        """

    async def aget_secret(self, name: str) -> str:
        """Async variant of :meth:`get_secret` (runs in a worker thread)."""
        return await asyncio.to_thread(self.get_secret, name)

    async def acreate_secret(self, name: str, value: str) -> None:
        """Async variant of :meth:`create_secret` (runs in a worker thread)."""
        return await asyncio.to_thread(self.create_secret, name, value)

    async def aupdate_secret(self, name: str, value: str) -> None:
        """Async variant of :meth:`update_secret` (runs in a worker thread)."""
        return await asyncio.to_thread(self.update_secret, name, value)

    async def adelete_secret(self, name: str) -> None:
        """Async variant of :meth:`delete_secret` (runs in a worker thread)."""
        return await asyncio.to_thread(self.delete_secret, name)
