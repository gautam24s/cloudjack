"""GCP Secret Manager implementation of the SecretManager blueprint."""

from google.cloud import secretmanager_v1
from google.api_core.exceptions import NotFound, AlreadyExists

from cloud.base.exceptions import (
    SecretManagerError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)

from cloud.base import SecretManagerBlueprint


class SecretManager(SecretManagerBlueprint):
    """GCP Secret Manager implementation for secret management.

    This provider implements the SecretManagerBlueprint interface for GCP Secret Manager,
    allowing creation, retrieval, updating, and deletion of secrets in GCP.

    Attributes:
        client: Google Cloud Secret Manager client for interacting with GCP Secret Manager API.
        project_id: The GCP project ID where secrets are stored.
    """

    def __init__(self, config: dict):
        """Initialize the GCP Secret Manager client.

        Args:
            config: Configuration dictionary containing GCP credentials and project ID.
                   Expected keys:
                   - project_id: GCP project ID where secrets are stored
                   - credentials: Optional Google Cloud credentials object (if not using default credentials)
        """
        self.client = secretmanager_v1.SecretManagerServiceClient(
            credentials=config.get("credentials")
        )
        self.project_id = config.get("project_id")

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
            return response.payload.data.decode("UTF-8")
        except NotFound:
            raise SecretNotFoundError(f"Secret '{name}' not found.")
        except Exception as e:
            raise SecretManagerError(f"Failed to retrieve secret '{name}': {str(e)}")

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
        except AlreadyExists:
            raise SecretAlreadyExistsError(f"Secret '{name}' already exists.")
        except Exception as e:
            raise SecretManagerError(f"Failed to create secret '{name}': {str(e)}")

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
        except NotFound:
            raise SecretNotFoundError(f"Secret '{name}' not found.")
        except Exception as e:
            raise SecretManagerError(f"Failed to update secret '{name}': {str(e)}")
    
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
        except NotFound:
            raise SecretNotFoundError(f"Secret '{name}' not found.")
        except Exception as e:
            raise SecretManagerError(f"Failed to delete secret '{name}': {str(e)}")
