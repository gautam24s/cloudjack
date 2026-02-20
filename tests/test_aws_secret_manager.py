from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.secret_manager import SecretManager
from cloud.base.config import AWSConfig
from cloud.base.exceptions import (
    SecretManagerError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)


def _client_error(code: str, message: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "op")


@pytest.fixture
def sm():
    with patch("cloud.aws.secret_manager.boto3") as mock_boto:
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_sm_client = MagicMock()

        def pick_client(service, **kwargs):
            return {"sts": mock_sts, "secretsmanager": mock_sm_client}[service]

        mock_boto.client.side_effect = pick_client

        instance = SecretManager(AWSConfig(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            region_name="us-east-1",
        ))
        yield instance, mock_sm_client


# --- get_secret ---


class TestGetSecret:
    def test_success(self, sm):
        instance, client = sm
        client.get_secret_value.return_value = {"SecretString": "my_value"}
        assert instance.get_secret("my_secret") == "my_value"
        client.get_secret_value.assert_called_once()

    def test_not_found(self, sm):
        instance, client = sm
        client.get_secret_value.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(SecretNotFoundError):
            instance.get_secret("missing")

    def test_generic_error(self, sm):
        instance, client = sm
        client.get_secret_value.side_effect = _client_error("InternalServiceError")
        with pytest.raises(SecretManagerError):
            instance.get_secret("fail")


# --- create_secret ---


class TestCreateSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.create_secret("new", "value")
        client.create_secret.assert_called_once_with(Name="new", SecretString="value")

    def test_already_exists(self, sm):
        instance, client = sm
        client.create_secret.side_effect = _client_error("ResourceExistsException")
        with pytest.raises(SecretAlreadyExistsError):
            instance.create_secret("dup", "value")

    def test_generic_error(self, sm):
        instance, client = sm
        client.create_secret.side_effect = _client_error("InternalServiceError")
        with pytest.raises(SecretManagerError):
            instance.create_secret("fail", "value")


# --- update_secret ---


class TestUpdateSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.update_secret("existing", "new_val")
        client.update_secret.assert_called_once()

    def test_not_found(self, sm):
        instance, client = sm
        client.update_secret.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(SecretNotFoundError):
            instance.update_secret("missing", "val")

    def test_generic_error(self, sm):
        instance, client = sm
        client.update_secret.side_effect = _client_error("InternalServiceError")
        with pytest.raises(SecretManagerError):
            instance.update_secret("fail", "val")


# --- delete_secret ---


class TestDeleteSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.delete_secret("existing")
        client.delete_secret.assert_called_once()

    def test_not_found(self, sm):
        instance, client = sm
        client.delete_secret.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(SecretNotFoundError):
            instance.delete_secret("missing")

    def test_generic_error(self, sm):
        instance, client = sm
        client.delete_secret.side_effect = _client_error("InternalServiceError")
        with pytest.raises(SecretManagerError):
            instance.delete_secret("fail")
