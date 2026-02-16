"""AWS Secrets Manager implementation of the SecretManager blueprint."""

import boto3
from botocore.exceptions import ClientError

from cloud.base.exceptions import (
    SecretManagerError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)

from cloud.base import SecretManagerBlueprint


class SecretManager(SecretManagerBlueprint):
    """AWS Secrets Manager implementation for secret management.
    
    This provider implements the SecretManagerBlueprint interface for AWS Secrets Manager,
    allowing creation, retrieval, updating, and deletion of secrets in AWS.
    
    Attributes:
        client: boto3 Secrets Manager client for interacting with AWS Secrets Manager API.
        region: AWS region name.
        account_id: AWS account ID retrieved from STS.
    """

    def __init__(self, config: dict):
        """Initialize the AWS Secret Manager client.
        
        Args:
            config: Configuration dictionary containing AWS credentials and region.
                   Expected keys:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "secretsmanager",
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            region_name=config.get("region_name"),
        )
        self.region = config.get("region_name")
        
        sts_client = boto3.client(
            "sts",
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            region_name=config.get("region_name"),
        )
        self.account_id = sts_client.get_caller_identity()["Account"]

    def get_secret(self, name: str) -> str:
        """Retrieve a secret value from AWS Secrets Manager.
        
        Args:
            name: The name of the secret to retrieve (ARN will be constructed automatically).
        
        Returns:
            The secret value as a string.
        
        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If retrieval fails for any other reason.
        """
        try:
            arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{name}"
            response = self.client.get_secret_value(SecretId=arn)
            return response.get("SecretString")  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{name}' not found.")
            else:
                raise SecretManagerError(
                    f"Failed to retrieve secret '{name}': {str(e)}"
                )

    def create_secret(self, name: str, value: str) -> None:
        """Create a new secret in AWS Secrets Manager.
        
        Args:
            name: The name of the secret to create.
            value: The secret value to store.
        
        Raises:
            SecretAlreadyExistsError: If a secret with the given name already exists.
            SecretManagerError: If creation fails for any other reason.
        """
        try:
            self.client.create_secret(Name=name, SecretString=value)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceExistsException":
                raise SecretAlreadyExistsError(f"Secret '{name}' already exists.")
            else:
                raise SecretManagerError(f"Failed to create secret '{name}': {str(e)}")

    def update_secret(self, name: str, value: str) -> None:
        """Update an existing secret in AWS Secrets Manager.
        
        Args:
            name: The name of the secret to update.
            value: The new secret value.
        
        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If update fails for any other reason.
        """
        try:
            arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{name}"
            self.client.update_secret(SecretId=arn, SecretString=value)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{name}' not found.")
            else:
                raise SecretManagerError(f"Failed to update secret '{name}': {str(e)}")

    def delete_secret(self, name: str) -> None:
        """Delete a secret from AWS Secrets Manager.
        
        This method permanently deletes the secret without recovery period.
        
        Args:
            name: The name of the secret to delete.
        
        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretManagerError: If deletion fails for any other reason.
        """
        try:
            arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{name}"
            self.client.delete_secret(SecretId=arn, ForceDeleteWithoutRecovery=True)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{name}' not found.")
            else:
                raise SecretManagerError(f"Failed to delete secret '{name}': {str(e)}")
