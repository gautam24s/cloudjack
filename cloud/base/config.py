"""
Pydantic configuration models for cloud provider configs.

Validates provider configs at initialization time instead of
silently passing bad values to SDK clients.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AWSConfig(BaseModel):
    """Configuration for AWS services.

    Credentials are resolved in order:
    1. Explicit values passed in the config dict.
    2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).
    3. If neither is set, fields are left as None so boto3 can fall back to its
       own credential chain (instance metadata, ~/.aws/credentials, etc.).
    """

    model_config = ConfigDict(extra="forbid")

    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")
    region_name: str | None = Field(default=None, description="AWS region (e.g. 'us-east-1')")

    @model_validator(mode="before")
    @classmethod
    def resolve_from_env(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Fall back to environment variables for missing credentials."""
        env_map = {
            "aws_access_key_id": "AWS_ACCESS_KEY_ID",
            "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
            "region_name": "AWS_DEFAULT_REGION",
        }
        for field, env_var in env_map.items():
            if not values.get(field):
                values[field] = os.environ.get(env_var)
        return values


class GCPConfig(BaseModel):
    """Configuration for GCP services.

    Credentials are resolved in order:
    1. Explicit values passed in the config dict.
    2. Environment variables (GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS).
    3. If neither is set, fields are left as None so the GCP SDK can fall back
       to Application Default Credentials (ADC).
    """

    model_config = ConfigDict(extra="forbid")

    project_id: str | None = Field(default=None, description="GCP project ID")
    credentials: Any | None = Field(default=None, description="GCP credentials object")
    credentials_path: str | None = Field(
        default=None, description="Path to service account JSON key file"
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_from_env(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Fall back to environment variables for missing config."""
        if not values.get("project_id"):
            values["project_id"] = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
                "GCLOUD_PROJECT"
            )
        if not values.get("credentials_path"):
            values["credentials_path"] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        return values

    @model_validator(mode="after")
    def validate_project_and_credentials(self) -> GCPConfig:
        """Ensure project_id is set and load credentials from path if needed."""
        if self.project_id is None:
            raise ValueError(
                "GCP project_id is required. Set it explicitly or via "
                "GOOGLE_CLOUD_PROJECT / GCLOUD_PROJECT environment variable."
            )
        if self.credentials is None and self.credentials_path:
            path = Path(self.credentials_path)
            if not path.exists():
                raise ValueError(f"Credentials file not found: {self.credentials_path}")
            from google.oauth2 import service_account  # lazy import

            self.credentials = service_account.Credentials.from_service_account_file(
                str(path)
            )
        return self


# Map provider names to their config models for dynamic validation
CONFIG_REGISTRY: dict[str, type[BaseModel]] = {
    "aws": AWSConfig,
    "gcp": GCPConfig,
}


def validate_config(cloud_provider: str, config: dict) -> BaseModel:
    """Validate and return a typed config model for the given provider.

    Args:
        cloud_provider: The cloud provider name (e.g. 'aws', 'gcp').
        config: Raw configuration dictionary.

    Returns:
        A validated Pydantic config model.

    Raises:
        ValueError: If the provider is unknown.
        pydantic.ValidationError: If the config is invalid.
    """
    model = CONFIG_REGISTRY.get(cloud_provider)
    if model is None:
        raise ValueError(f"No config model registered for provider: {cloud_provider}")
    return model(**config)


__all__ = [
    "AWSConfig",
    "GCPConfig",
    "CONFIG_REGISTRY",
    "validate_config",
]
