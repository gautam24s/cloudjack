from unittest.mock import patch, MagicMock
import pytest
from google.api_core.exceptions import NotFound, AlreadyExists

from cloud.gcp.secret_manager import SecretManager
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    SecretManagerError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)


@pytest.fixture
def sm():
    with patch("cloud.gcp.secret_manager.secretmanager_v1") as mock_sm:
        mock_client = MagicMock()
        mock_sm.SecretManagerServiceClient.return_value = mock_client
        instance = SecretManager(GCPConfig(project_id="my-project"))
        yield instance, mock_client


# --- get_secret ---


class TestGetSecret:
    def test_success(self, sm):
        instance, client = sm
        mock_response = MagicMock()
        mock_response.payload.data = b"my_value"
        client.access_secret_version.return_value = mock_response
        assert instance.get_secret("my_secret") == "my_value"
        client.access_secret_version.assert_called_once_with(
            name="projects/my-project/secrets/my_secret/versions/latest"
        )

    def test_not_found(self, sm):
        instance, client = sm
        client.access_secret_version.side_effect = NotFound("not found")
        with pytest.raises(SecretNotFoundError):
            instance.get_secret("missing")

    def test_generic_error(self, sm):
        instance, client = sm
        client.access_secret_version.side_effect = RuntimeError("boom")
        with pytest.raises(SecretManagerError):
            instance.get_secret("fail")


# --- create_secret ---


class TestCreateSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.create_secret("new", "value")
        client.create_secret.assert_called_once()
        client.add_secret_version.assert_called_once()

    def test_already_exists(self, sm):
        instance, client = sm
        client.create_secret.side_effect = AlreadyExists("exists")
        with pytest.raises(SecretAlreadyExistsError):
            instance.create_secret("dup", "value")

    def test_generic_error(self, sm):
        instance, client = sm
        client.create_secret.side_effect = RuntimeError("boom")
        with pytest.raises(SecretManagerError):
            instance.create_secret("fail", "value")


# --- update_secret ---


class TestUpdateSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.update_secret("existing", "new_val")
        client.get_secret.assert_called_once_with(
            name="projects/my-project/secrets/existing"
        )
        client.add_secret_version.assert_called_once()

    def test_not_found(self, sm):
        instance, client = sm
        client.get_secret.side_effect = NotFound("not found")
        with pytest.raises(SecretNotFoundError):
            instance.update_secret("missing", "val")

    def test_generic_error(self, sm):
        instance, client = sm
        client.get_secret.side_effect = RuntimeError("boom")
        with pytest.raises(SecretManagerError):
            instance.update_secret("fail", "val")


# --- delete_secret ---


class TestDeleteSecret:
    def test_success(self, sm):
        instance, client = sm
        instance.delete_secret("existing")
        client.delete_secret.assert_called_once_with(
            name="projects/my-project/secrets/existing"
        )

    def test_not_found(self, sm):
        instance, client = sm
        client.delete_secret.side_effect = NotFound("not found")
        with pytest.raises(SecretNotFoundError):
            instance.delete_secret("missing")

    def test_generic_error(self, sm):
        instance, client = sm
        client.delete_secret.side_effect = RuntimeError("boom")
        with pytest.raises(SecretManagerError):
            instance.delete_secret("fail")
