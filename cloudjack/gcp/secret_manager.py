"""GCP Secret Manager implementation of the SecretManagerService interface."""

from google.cloud import secretmanager_v1
from google.api_core.exceptions import (
    AlreadyExists,
    GoogleAPICallError,
    NotFound,
)

from cloudjack.base.exceptions import (
    SecretManagerError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)

from cloudjack.base import SecretManagerService
from cloudjack.base.config import GCPConfig


class SecretManager(SecretManagerService):
    """GCP Secret Manager implementation for secret management.

    This provider implements the SecretManagerService interface for GCP Secret Manager,
    allowing creation, retrieval, updating, and deletion of secrets in GCP.

    Attributes:
        client: Google Cloud Secret Manager client for interacting with GCP Secret Manager API.
        project_id: The GCP project ID where secrets are stored.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize the GCP Secret Manager client.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID where secrets are stored
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        self.client = secretmanager_v1.SecretManagerServiceClient(
            credentials=config.credentials
        )
        self.project_id = config.project_id

    def get_secret(self, name: str) -> str:
        """Retrieve a secret value from GCP Secret Manager.

        Args:
            name: The name of the secret to retrieve (e.g., 'my-secret').

        Returns:
            The secret value as a string.

        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If retrieval fails for any other reason.
        """
        secret_name = f"projects/{self.project_id}/secrets/{name}/versions/latest"
        try:
            response = self.client.access_secret_version(name=secret_name)
            return str(response.payload.data.decode("UTF-8"))
        except NotFound as e:
            raise SecretNotFoundError(f"Secret '{name}' not found.") from e
        except GoogleAPICallError as e:
            raise SecretManagerError(f"Failed to retrieve secret '{name}'") from e

    def create_secret(self, name: str, value: str) -> None:
        """Create a new secret in GCP Secret Manager.

        Args:
            name: The name of the secret to create (e.g., 'my-secret').
            value: The value of the secret to store.

        Raises:
            SecretAlreadyExistsError: If a secret with the given name already exists.
            SecretManagerError: If creation fails for any other reason.
        """
        parent = f"projects/{self.project_id}"
        try:
            self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            self.client.add_secret_version(
                request={
                    "parent": f"{parent}/secrets/{name}",
                    "payload": {"data": value.encode("UTF-8")},
                }
            )
        except AlreadyExists as e:
            raise SecretAlreadyExistsError(f"Secret '{name}' already exists.") from e
        except GoogleAPICallError as e:
            raise SecretManagerError(f"Failed to create secret '{name}'") from e

    def update_secret(self, name: str, value: str) -> None:
        """Update an existing secret in GCP Secret Manager.

        Args:
            name: The name of the secret to update (e.g., 'my-secret').
            value: The new value of the secret to store.
        
        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If update fails for any other reason.
        """
        secret_name = f"projects/{self.project_id}/secrets/{name}"
        try:
            # Check if the secret exists
            self.client.get_secret(name=secret_name)
            # Add a new version with the updated value
            self.client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": value.encode("UTF-8")},
                }
            )
        except NotFound as e:
            raise SecretNotFoundError(f"Secret '{name}' not found.") from e
        except GoogleAPICallError as e:
            raise SecretManagerError(f"Failed to update secret '{name}'") from e
    
    def delete_secret(self, name: str) -> None:
        """Delete a secret from GCP Secret Manager.

        Args:
            name: The name of the secret to delete (e.g., 'my-secret').

        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If deletion fails for any other reason.
        """
        secret_name = f"projects/{self.project_id}/secrets/{name}"
        try:
            self.client.delete_secret(name=secret_name)
        except NotFound as e:
            raise SecretNotFoundError(f"Secret '{name}' not found.") from e
        except GoogleAPICallError as e:
            raise SecretManagerError(f"Failed to delete secret '{name}'") from e
