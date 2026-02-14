"""Cloud storage service blueprint."""

from abc import ABC, abstractmethod


class CloudStorageBlueprint(ABC):
    """Abstract interface for cloud storage operations.

    Defines bucket and object CRUD, plus signed-URL generation.
    Maps to AWS S3 and GCP Cloud Storage.
    """

    # --- Bucket operations ---

    @abstractmethod
    def create_bucket(self, bucket_name: str) -> None:
        """Create a new storage bucket.

        Args:
            bucket_name: Globally unique bucket name.
        """
        pass

    @abstractmethod
    def delete_bucket(self, bucket_name: str) -> None:
        """Delete an empty storage bucket.

        Args:
            bucket_name: Name of the bucket to delete.
        """
        pass

    @abstractmethod
    def list_buckets(self) -> list[str]:
        """List all bucket names owned by the authenticated account.

        Returns:
            A list of bucket name strings.
        """
        pass

    # --- Object operations ---

    @abstractmethod
    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Upload a local file to a storage bucket.

        Args:
            bucket_name: Target bucket.
            object_name: Destination object key.
            file_path: Local filesystem path to upload.
        """
        pass

    @abstractmethod
    def download_file(self, bucket_name: str, object_name: str, destination: str) -> None:
        """Download an object to a local file.

        Args:
            bucket_name: Source bucket.
            object_name: Object key to download.
            destination: Local path to write the downloaded file.
        """
        pass

    @abstractmethod
    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from a storage bucket.

        Args:
            bucket_name: Bucket containing the object.
            object_name: Object key to delete.
        """
        pass

    @abstractmethod
    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List object keys in a bucket.

        Args:
            bucket_name: Bucket to list.
            prefix: Optional key prefix filter.

        Returns:
            A list of object key strings.
        """
        pass

    @abstractmethod
    def get_object(self, bucket_name: str, object_name: str) -> bytes:
        """Read the contents of an object.

        Args:
            bucket_name: Bucket containing the object.
            object_name: Object key to read.

        Returns:
            The raw object bytes.
        """
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