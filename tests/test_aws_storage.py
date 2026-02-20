from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.storage import Storage
from cloud.base.config import AWSConfig
from cloud.base.exceptions import (
    StorageError,
    BucketNotFoundError,
    BucketAlreadyExistsError,
    ObjectNotFoundError,
)


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "err"}}, "op")


@pytest.fixture
def storage():
    with patch("cloud.aws.storage.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = Storage(AWSConfig(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            region_name="ap-south-1",
        ))
        yield instance, mock_client


# --- Bucket operations ---


class TestCreateBucket:
    def test_success(self, storage):
        instance, client = storage
        instance.create_bucket("my-bucket")
        client.create_bucket.assert_called_once()

    def test_includes_location_constraint_for_non_us_east_1(self, storage):
        instance, client = storage
        instance.create_bucket("my-bucket")
        call_kwargs = client.create_bucket.call_args
        assert "CreateBucketConfiguration" in call_kwargs.kwargs

    def test_already_exists(self, storage):
        instance, client = storage
        client.create_bucket.side_effect = _client_error("BucketAlreadyExists")
        with pytest.raises(BucketAlreadyExistsError):
            instance.create_bucket("dup")

    def test_already_owned(self, storage):
        instance, client = storage
        client.create_bucket.side_effect = _client_error("BucketAlreadyOwnedByYou")
        with pytest.raises(BucketAlreadyExistsError):
            instance.create_bucket("dup")

    def test_generic_error(self, storage):
        instance, client = storage
        client.create_bucket.side_effect = _client_error("AccessDenied")
        with pytest.raises(StorageError):
            instance.create_bucket("fail")


class TestDeleteBucket:
    def test_success(self, storage):
        instance, client = storage
        instance.delete_bucket("my-bucket")
        client.delete_bucket.assert_called_once_with(Bucket="my-bucket")

    def test_not_found(self, storage):
        instance, client = storage
        client.delete_bucket.side_effect = _client_error("NoSuchBucket")
        with pytest.raises(BucketNotFoundError):
            instance.delete_bucket("missing")


class TestListBuckets:
    def test_success(self, storage):
        instance, client = storage
        client.list_buckets.return_value = {
            "Buckets": [{"Name": "a"}, {"Name": "b"}]
        }
        assert instance.list_buckets() == ["a", "b"]

    def test_empty(self, storage):
        instance, client = storage
        client.list_buckets.return_value = {"Buckets": []}
        assert instance.list_buckets() == []

    def test_error(self, storage):
        instance, client = storage
        client.list_buckets.side_effect = _client_error("AccessDenied")
        with pytest.raises(StorageError):
            instance.list_buckets()


# --- Object operations ---


class TestUploadFile:
    def test_success(self, storage):
        instance, client = storage
        instance.upload_file("bucket", "key", "/tmp/file")
        client.upload_file.assert_called_once_with("/tmp/file", "bucket", "key")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        client.upload_file.side_effect = _client_error("NoSuchBucket")
        with pytest.raises(BucketNotFoundError):
            instance.upload_file("missing", "key", "/tmp/file")


class TestDownloadFile:
    def test_success(self, storage):
        instance, client = storage
        instance.download_file("bucket", "key", "/tmp/dest")
        client.download_file.assert_called_once_with("bucket", "key", "/tmp/dest")

    def test_object_not_found(self, storage):
        instance, client = storage
        client.download_file.side_effect = _client_error("404")
        with pytest.raises(ObjectNotFoundError):
            instance.download_file("bucket", "missing", "/tmp/dest")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        client.download_file.side_effect = _client_error("NoSuchBucket")
        with pytest.raises(BucketNotFoundError):
            instance.download_file("missing", "key", "/tmp/dest")


class TestDeleteObject:
    def test_success(self, storage):
        instance, client = storage
        instance.delete_object("bucket", "key")
        client.delete_object.assert_called_once_with(Bucket="bucket", Key="key")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        client.delete_object.side_effect = _client_error("NoSuchBucket")
        with pytest.raises(BucketNotFoundError):
            instance.delete_object("missing", "key")


class TestListObjects:
    def test_success(self, storage):
        instance, client = storage
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "a.txt"}, {"Key": "b.txt"}]},
            {"Contents": [{"Key": "c.txt"}]},
        ]
        client.get_paginator.return_value = paginator
        assert instance.list_objects("bucket") == ["a.txt", "b.txt", "c.txt"]

    def test_empty(self, storage):
        instance, client = storage
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        client.get_paginator.return_value = paginator
        assert instance.list_objects("bucket") == []

    def test_with_prefix(self, storage):
        instance, client = storage
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "data/a.csv"}]},
        ]
        client.get_paginator.return_value = paginator
        instance.list_objects("bucket", prefix="data/")
        paginator.paginate.assert_called_once_with(Bucket="bucket", Prefix="data/")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        paginator = MagicMock()
        paginator.paginate.side_effect = _client_error("NoSuchBucket")
        client.get_paginator.return_value = paginator
        with pytest.raises(BucketNotFoundError):
            instance.list_objects("missing")


class TestGetObject:
    def test_success(self, storage):
        instance, client = storage
        body = MagicMock()
        body.read.return_value = b"hello"
        client.get_object.return_value = {"Body": body}
        assert instance.get_object("bucket", "key") == b"hello"

    def test_not_found(self, storage):
        instance, client = storage
        client.get_object.side_effect = _client_error("NoSuchKey")
        with pytest.raises(ObjectNotFoundError):
            instance.get_object("bucket", "missing")

    def test_bucket_not_found(self, storage):
        instance, client = storage
        client.get_object.side_effect = _client_error("NoSuchBucket")
        with pytest.raises(BucketNotFoundError):
            instance.get_object("missing", "key")


class TestGenerateSignedUrl:
    def test_defaults(self, storage):
        instance, client = storage
        client.generate_presigned_url.return_value = "https://signed-url"
        url = instance.generate_signed_url("bucket", "key", 3600)
        assert url == "https://signed-url"
        client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "bucket", "Key": "key"},
            ExpiresIn=3600,
            HttpMethod="GET",
        )

    def test_put_method_with_content_type(self, storage):
        instance, client = storage
        client.generate_presigned_url.return_value = "https://put-url"
        url = instance.generate_signed_url(
            "bucket", "key", 7200,
            method="PUT",
            content_type="application/json",
        )
        assert url == "https://put-url"
        client.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={
                "Bucket": "bucket",
                "Key": "key",
                "ContentType": "application/json",
            },
            ExpiresIn=7200,
            HttpMethod="PUT",
        )

    def test_response_params(self, storage):
        instance, client = storage
        client.generate_presigned_url.return_value = "https://dl-url"
        url = instance.generate_signed_url(
            "bucket", "key", 3600,
            response_disposition='attachment; filename="f.txt"',
            response_type="application/octet-stream",
        )
        assert url == "https://dl-url"
        client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "bucket",
                "Key": "key",
                "ResponseContentDisposition": 'attachment; filename="f.txt"',
                "ResponseContentType": "application/octet-stream",
            },
            ExpiresIn=3600,
            HttpMethod="GET",
        )

    def test_delete_method(self, storage):
        instance, client = storage
        client.generate_presigned_url.return_value = "https://del-url"
        url = instance.generate_signed_url("bucket", "key", 900, method="DELETE")
        assert url == "https://del-url"
        client.generate_presigned_url.assert_called_once_with(
            "delete_object",
            Params={"Bucket": "bucket", "Key": "key"},
            ExpiresIn=900,
            HttpMethod="DELETE",
        )

    def test_error(self, storage):
        instance, client = storage
        client.generate_presigned_url.side_effect = _client_error("AccessDenied")
        with pytest.raises(StorageError):
            instance.generate_signed_url("bucket", "key", 3600)
