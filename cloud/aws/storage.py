"""AWS S3 implementation of the Storage blueprint."""

import boto3
from typing import NoReturn
from botocore.exceptions import ClientError

from cloud.base.exceptions import (
    StorageError,
    BucketNotFoundError,
    BucketAlreadyExistsError,
    ObjectNotFoundError,
)
from cloud.base import CloudStorageBlueprint
from cloud.base.config import AWSConfig

_ERROR_MAP = {
    "NoSuchBucket": BucketNotFoundError,
    "NoSuchKey": ObjectNotFoundError,
    "404": ObjectNotFoundError,
    "BucketAlreadyExists": BucketAlreadyExistsError,
    "BucketAlreadyOwnedByYou": BucketAlreadyExistsError,
}


def _handle_client_error(e: ClientError, message: str) -> NoReturn:
    """Raise a mapped exception or a generic StorageError."""
    exc_class = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc_class or StorageError)(message) from e


class Storage(CloudStorageBlueprint):
    """AWS S3 implementation for cloud storage operations.

    Provides CRUD operations for S3 buckets and objects.

    Attributes:
        client: boto3 S3 client for interacting with the AWS S3 API.
        region: AWS region name.
    """

    def __init__(self, config: AWSConfig) -> None:
        """Initialize the AWS S3 client.

        Args:
            config: AWS configuration object containing credentials and region.
                   Expected attributes:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "s3",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )
        self.region = config.region_name

    # --- Bucket operations ---

    def create_bucket(self, bucket_name: str) -> None:
        """Create a new S3 bucket.

        Args:
            bucket_name: The name of the bucket to create.

        Raises:
            BucketAlreadyExistsError: If the bucket already exists.
            StorageError: If creation fails for any other reason.
        """
        try:
            create_config = {}
            if self.region and self.region != "us-east-1":
                create_config["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.region
                }
            self.client.create_bucket(Bucket=bucket_name, **create_config)
        except ClientError as e:
            _handle_client_error(e, f"Failed to create bucket '{bucket_name}'.")

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete an S3 bucket.

        The bucket must be empty before deletion.

        Args:
            bucket_name: The name of the bucket to delete.

        Raises:
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If deletion fails for any other reason.
        """
        try:
            self.client.delete_bucket(Bucket=bucket_name)
        except ClientError as e:
            _handle_client_error(e, f"Failed to delete bucket '{bucket_name}'.")

    def list_buckets(self) -> list[str]:
        """List all S3 buckets owned by the authenticated user.

        Returns:
            A list of bucket names.

        Raises:
            StorageError: If listing fails.
        """
        try:
            response = self.client.list_buckets()
            return [bucket["Name"] for bucket in response.get("Buckets", [])]
        except ClientError as e:
            _handle_client_error(e, "Failed to list buckets.")

    # --- Object operations ---

    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Upload a file to an S3 bucket.

        Args:
            bucket_name: The name of the target bucket.
            object_name: The S3 object key to assign to the uploaded file.
            file_path: The local path of the file to upload.

        Raises:
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If upload fails for any other reason.
        """
        try:
            self.client.upload_file(file_path, bucket_name, object_name)
        except ClientError as e:
            _handle_client_error(e, f"Failed to upload '{object_name}' to '{bucket_name}'.")

    def download_file(self, bucket_name: str, object_name: str, destination: str) -> None:
        """Download a file from an S3 bucket.

        Args:
            bucket_name: The name of the source bucket.
            object_name: The S3 object key to download.
            destination: The local file path to save the downloaded file.

        Raises:
            ObjectNotFoundError: If the object does not exist.
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If download fails for any other reason.
        """
        try:
            self.client.download_file(bucket_name, object_name, destination)
        except ClientError as e:
            _handle_client_error(e, f"Failed to download '{object_name}' from '{bucket_name}'.")

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from an S3 bucket.

        Args:
            bucket_name: The name of the bucket containing the object.
            object_name: The S3 object key to delete.

        Raises:
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If deletion fails for any other reason.
        """
        try:
            self.client.delete_object(Bucket=bucket_name, Key=object_name)
        except ClientError as e:
            _handle_client_error(e, f"Failed to delete '{object_name}' from '{bucket_name}'.")

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List objects in an S3 bucket, optionally filtered by prefix.

        Handles pagination automatically to return all matching keys.

        Args:
            bucket_name: The name of the bucket to list objects from.
            prefix: Optional prefix to filter object keys.

        Returns:
            A list of object keys.

        Raises:
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If listing fails for any other reason.
        """
        try:
            keys: list[str] = []
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                keys.extend(obj["Key"] for obj in page.get("Contents", []))
            return keys
        except ClientError as e:
            _handle_client_error(e, f"Failed to list objects in '{bucket_name}'.")

    def get_object(self, bucket_name: str, object_name: str) -> bytes:
        """Get the contents of an S3 object as bytes.

        Args:
            bucket_name: The name of the bucket containing the object.
            object_name: The S3 object key to retrieve.

        Returns:
            The object contents as bytes.

        Raises:
            ObjectNotFoundError: If the object does not exist.
            BucketNotFoundError: If the bucket does not exist.
            StorageError: If retrieval fails for any other reason.
        """
        try:
            response = self.client.get_object(Bucket=bucket_name, Key=object_name)
            return response["Body"].read()  # type: ignore[no-any-return]
        except ClientError as e:
            _handle_client_error(e, f"Failed to get '{object_name}' from '{bucket_name}'.")

    _METHOD_TO_CLIENT_METHOD = {
        "GET": "get_object",
        "PUT": "put_object",
        "DELETE": "delete_object",
        "HEAD": "head_object",
    }

    def generate_signed_url(
        self,
        bucket_name: str,
        object_name: str,
        expiration: int,
        method: str = "GET",
        **kwargs,
    ) -> str:
        """Generate a pre-signed URL for accessing an S3 object.

        Args:
            bucket_name: The name of the bucket containing the object.
            object_name: The S3 object key.
            expiration: URL expiration time in seconds.
            method: HTTP method the URL will allow (GET, PUT, DELETE, HEAD).
        
            **kwargs: Additional keyword arguments for provider-specific options:
                content_type: Content-Type for the signed request (only for PUT/POST).
                response_disposition: Content-Disposition header in the response.
                response_type: Content-Type header in the response.

        Returns:
            A pre-signed URL string.

        Raises:
            StorageError: If URL generation fails.
        """
        try:
            client_method = self._METHOD_TO_CLIENT_METHOD.get(method.upper(), "get_object")
            params: dict = {"Bucket": bucket_name, "Key": object_name}
            
            # ContentType is only valid for PUT/POST requests (constrains the request)
            if kwargs.get("content_type") and method.upper() in ("PUT", "POST"):
                params["ContentType"] = kwargs["content_type"]
            
            # Response headers can be set for any method
            if kwargs.get("response_disposition"):
                params["ResponseContentDisposition"] = kwargs["response_disposition"]
            if kwargs.get("response_type"):
                params["ResponseContentType"] = kwargs["response_type"]
            
            return self.client.generate_presigned_url(  # type: ignore[no-any-return]
                client_method,
                Params=params,
                ExpiresIn=expiration,
                HttpMethod=method.upper(),
            )
        except ClientError as e:
            _handle_client_error(e, f"Failed to generate signed URL for '{object_name}'.")
