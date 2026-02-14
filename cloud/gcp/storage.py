from datetime import timedelta
from google.cloud import storage as gcs
from google.api_core.exceptions import NotFound, Conflict
from google.cloud.exceptions import GoogleCloudError

from cloud.base.exceptions import (
    StorageError,
    BucketNotFoundError,
    BucketAlreadyExistsError,
    ObjectNotFoundError,
)
from cloud.base import CloudStorageBlueprint


def _handle_error(e: Exception, message: str):
    """Raise a mapped exception or a generic StorageError."""
    if isinstance(e, NotFound):
        if "bucket" in str(e).lower():
            raise BucketNotFoundError(message) from e
        raise ObjectNotFoundError(message) from e
    if isinstance(e, Conflict):
        raise BucketAlreadyExistsError(message) from e
    raise StorageError(message) from e


class Storage(CloudStorageBlueprint):
    """GCP Cloud Storage implementation for cloud storage CRUD operations."""

    def __init__(self, config: dict):
        """Initialize the GCP Cloud Storage client.

        Args:
            config: Dict with project_id and optional credentials.
        """
        self.client = gcs.Client(
            project=config.get("project_id"),
            credentials=config.get("credentials"),
        )

    def create_bucket(self, bucket_name: str) -> None:
        """Create a new GCS bucket."""
        try:
            self.client.create_bucket(bucket_name)
        except (GoogleCloudError, Conflict) as e:
            _handle_error(e, f"Failed to create bucket '{bucket_name}'.")

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a GCS bucket. Must be empty."""
        try:
            bucket = self.client.get_bucket(bucket_name)
            bucket.delete()
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to delete bucket '{bucket_name}'.")

    def list_buckets(self) -> list[str]:
        """List all GCS bucket names."""
        try:
            return [b.name for b in self.client.list_buckets()]
        except GoogleCloudError as e:
            _handle_error(e, "Failed to list buckets.")

    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Upload a local file to GCS."""
        try:
            bucket = self.client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_filename(file_path)
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to upload '{object_name}' to '{bucket_name}'.")

    def download_file(self, bucket_name: str, object_name: str, destination: str) -> None:
        """Download a GCS object to a local file."""
        try:
            bucket = self.client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.download_to_filename(destination)
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to download '{object_name}' from '{bucket_name}'.")

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from GCS."""
        try:
            bucket = self.client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.delete()
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to delete '{object_name}' from '{bucket_name}'.")

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List object names in a GCS bucket, optionally filtered by prefix."""
        try:
            blobs = self.client.list_blobs(bucket_name, prefix=prefix or None)
            return [blob.name for blob in blobs]
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to list objects in '{bucket_name}'.")

    def get_object(self, bucket_name: str, object_name: str) -> bytes:
        """Get the contents of a GCS object as bytes."""
        try:
            bucket = self.client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            return blob.download_as_bytes()
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to get '{object_name}' from '{bucket_name}'.")

    def generate_signed_url(
        self,
        bucket_name: str,
        object_name: str,
        expiration: int,
        method: str = "GET",
        **kwargs,
    ) -> str:
        """Generate a signed URL for a GCS object.

        Args:
            bucket_name: The name of the bucket containing the object.
            object_name: The object name/key.
            expiration: URL expiration time in seconds.
            method: HTTP method (GET, PUT, DELETE, etc.). Defaults to "GET".
            **kwargs: Additional keyword arguments for provider-specific options:
                content_type: Content-Type for the signed request.
                response_disposition: Content-Disposition header in the response.
                response_type: Content-Type header in the response.
                version: Signing version ("v2" or "v4"). Defaults to "v4".
                scheme: URL scheme ("http" or "https"). Defaults to "https".

        Returns:
            A signed URL string.

        Raises:
            StorageError: If URL generation fails.

        Note: Requires a service account key (JSON credentials) for signing.
        """
        
        try:
            bucket = self.client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            expiration_td = timedelta(seconds=expiration)
            return blob.generate_signed_url(
                expiration=expiration_td,
                method=method,
                content_type=kwargs.get("content_type"),
                response_disposition=kwargs.get("response_disposition"),
                response_type=kwargs.get("response_type"),
                version=kwargs.get("version", "v4"),
                scheme=kwargs.get("scheme", "https"),
            )
        except (GoogleCloudError, NotFound) as e:
            _handle_error(e, f"Failed to generate signed URL for '{object_name}'.")
