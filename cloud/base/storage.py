from abc import ABC, abstractmethod


class CloudStorageBlueprint(ABC):
    """Abstract base class for cloud storage operations.
    
    Defines the interface for CRUD operations on storage buckets and objects
    across different cloud providers.
    """

    # --- Bucket operations ---

    @abstractmethod
    def create_bucket(self, bucket_name: str) -> None:
        """Create a new storage bucket."""
        pass

    @abstractmethod
    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a storage bucket."""
        pass

    @abstractmethod
    def list_buckets(self) -> list[str]:
        """List all storage buckets."""
        pass

    # --- Object operations ---

    @abstractmethod
    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Upload a file to a storage bucket."""
        pass

    @abstractmethod
    def download_file(self, bucket_name: str, object_name: str, destination: str) -> None:
        """Download a file from a storage bucket."""
        pass

    @abstractmethod
    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from a storage bucket."""
        pass

    @abstractmethod
    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List objects in a storage bucket, optionally filtered by prefix."""
        pass

    @abstractmethod
    def get_object(self, bucket_name: str, object_name: str) -> bytes:
        """Get the contents of an object as bytes."""
        pass

    @abstractmethod
    def generate_signed_url(
        self,
        bucket_name: str,
        object_name: str,
        expiration: int,
        method: str = "GET",
        **kwargs
    ) -> str:
        """Generate a pre-signed URL for accessing an object.

        Args:
            bucket_name: The name of the bucket containing the object.
            object_name: The object key/name.
            expiration: URL expiration time in seconds.
            method: HTTP method the URL will allow (GET, PUT, DELETE, etc.).
            **kwargs: Additional keyword arguments for provider-specific options:
                AWS (S3):
                    - content_type: Content-Type for the request.
                    - response_disposition: Content-Disposition header in response.
                    - response_type: Content-Type header in response.
                GCP (Cloud Storage):
                    - content_type: Content-Type for the signed request.
                    - response_disposition: Content-Disposition header in response.
                    - response_type: Content-Type header in response.
                    - version: Signing version ("v2" or "v4", default "v4").
                    - scheme: URL scheme ("http" or "https", default "https").

        Returns:
            A pre-signed URL string.
        """
        pass