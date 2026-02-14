from unittest.mock import patch, MagicMock, call
from datetime import timedelta
import pytest
from google.api_core.exceptions import NotFound, Conflict
from google.cloud.exceptions import GoogleCloudError

from cloud.gcp.storage import Storage
from cloud.base.exceptions import (
    StorageError,
    BucketNotFoundError,
    BucketAlreadyExistsError,
    ObjectNotFoundError,
)


@pytest.fixture
def storage():
    with patch("cloud.gcp.storage.gcs") as mock_gcs:
        mock_client = MagicMock()
        mock_gcs.Client.return_value = mock_client
        instance = Storage({"project_id": "my-project"})
        yield instance, mock_client


# --- Bucket operations ---


class TestCreateBucket:
    def test_success(self, storage):
        instance, client = storage
        instance.create_bucket("my-bucket")
        client.create_bucket.assert_called_once_with("my-bucket")

    def test_conflict(self, storage):
        instance, client = storage
        client.create_bucket.side_effect = Conflict("exists")
        with pytest.raises(BucketAlreadyExistsError):
            instance.create_bucket("dup")

    def test_generic_error(self, storage):
        instance, client = storage
        client.create_bucket.side_effect = GoogleCloudError("fail")
        with pytest.raises(StorageError):
            instance.create_bucket("fail")


class TestDeleteBucket:
    def test_success(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        client.get_bucket.return_value = mock_bucket
        instance.delete_bucket("my-bucket")
        client.get_bucket.assert_called_once_with("my-bucket")
        mock_bucket.delete.assert_called_once()

    def test_not_found(self, storage):
        instance, client = storage
        client.get_bucket.side_effect = NotFound("bucket not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.delete_bucket("missing")


class TestListBuckets:
    def test_success(self, storage):
        instance, client = storage
        b1, b2 = MagicMock(), MagicMock()
        b1.name, b2.name = "a", "b"
        client.list_buckets.return_value = [b1, b2]
        assert instance.list_buckets() == ["a", "b"]

    def test_empty(self, storage):
        instance, client = storage
        client.list_buckets.return_value = []
        assert instance.list_buckets() == []

    def test_error(self, storage):
        instance, client = storage
        client.list_buckets.side_effect = GoogleCloudError("fail")
        with pytest.raises(StorageError):
            instance.list_buckets()


# --- Object operations ---


class TestUploadFile:
    def test_success(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        instance.upload_file("bucket", "key", "/tmp/file")
        mock_blob.upload_from_filename.assert_called_once_with("/tmp/file")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        client.get_bucket.side_effect = NotFound("bucket not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.upload_file("missing", "key", "/tmp/file")


class TestDownloadFile:
    def test_success(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        instance.download_file("bucket", "key", "/tmp/dest")
        mock_blob.download_to_filename.assert_called_once_with("/tmp/dest")

    def test_not_found(self, storage):
        instance, client = storage
        client.get_bucket.side_effect = NotFound("not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.download_file("bucket", "missing", "/tmp/dest")


class TestDeleteObject:
    def test_success(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        instance.delete_object("bucket", "key")
        mock_blob.delete.assert_called_once()

    def test_not_found(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.delete.side_effect = NotFound("not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.delete_object("bucket", "missing")


class TestListObjects:
    def test_success(self, storage):
        instance, client = storage
        b1, b2 = MagicMock(), MagicMock()
        b1.name, b2.name = "a.txt", "b.txt"
        client.list_blobs.return_value = [b1, b2]
        assert instance.list_objects("bucket") == ["a.txt", "b.txt"]

    def test_with_prefix(self, storage):
        instance, client = storage
        client.list_blobs.return_value = []
        instance.list_objects("bucket", prefix="data/")
        client.list_blobs.assert_called_once_with("bucket", prefix="data/")

    def test_not_found(self, storage):
        instance, client = storage
        client.list_blobs.side_effect = NotFound("not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.list_objects("missing")


class TestGetObject:
    def test_success(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.download_as_bytes.return_value = b"hello"
        assert instance.get_object("bucket", "key") == b"hello"

    def test_not_found(self, storage):
        instance, client = storage
        client.get_bucket.side_effect = NotFound("not found")
        with pytest.raises((BucketNotFoundError, ObjectNotFoundError)):
            instance.get_object("bucket", "missing")


class TestGenerateSignedUrl:
    def test_defaults(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed-url"
        url = instance.generate_signed_url("bucket", "key", 3600)
        assert url == "https://signed-url"
        mock_blob.generate_signed_url.assert_called_once_with(
            expiration=timedelta(seconds=3600),
            method="GET",
            content_type=None,
            response_disposition=None,
            response_type=None,
            version="v4",
            scheme="https",
        )

    def test_custom_method_and_content_type(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://put-url"
        url = instance.generate_signed_url(
            "bucket", "key", 7200,
            method="PUT",
            content_type="application/json",
        )
        assert url == "https://put-url"
        mock_blob.generate_signed_url.assert_called_once_with(
            expiration=timedelta(seconds=7200),
            method="PUT",
            content_type="application/json",
            response_disposition=None,
            response_type=None,
            version="v4",
            scheme="https",
        )

    def test_response_params(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://dl-url"
        url = instance.generate_signed_url(
            "bucket", "key", 3600,
            response_disposition='attachment; filename="f.txt"',
            response_type="application/octet-stream",
        )
        assert url == "https://dl-url"
        mock_blob.generate_signed_url.assert_called_once_with(
            expiration=timedelta(seconds=3600),
            method="GET",
            content_type=None,
            response_disposition='attachment; filename="f.txt"',
            response_type="application/octet-stream",
            version="v4",
            scheme="https",
        )

    def test_v2_and_http_scheme(self, storage):
        instance, client = storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "http://v2-url"
        url = instance.generate_signed_url(
            "bucket", "key", 900, version="v2", scheme="http",
        )
        assert url == "http://v2-url"
        mock_blob.generate_signed_url.assert_called_once_with(
            expiration=timedelta(seconds=900),
            method="GET",
            content_type=None,
            response_disposition=None,
            response_type=None,
            version="v2",
            scheme="http",
        )

    def test_error(self, storage):
        instance, client = storage
        client.get_bucket.side_effect = GoogleCloudError("fail")
        with pytest.raises(StorageError):
            instance.generate_signed_url("bucket", "key", 3600)
