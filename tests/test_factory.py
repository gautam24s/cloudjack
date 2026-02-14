from unittest.mock import patch, MagicMock
import pytest

from cloud.factory import universal_factory
from cloud.base import SecretManagerBlueprint, CloudStorageBlueprint


class TestUniversalFactory:
    @patch("cloud.aws.secret_manager.boto3")
    def test_aws_secret_manager(self, mock_boto):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_sm = MagicMock()

        def pick(service, **kw):
            return {"sts": mock_sts, "secretsmanager": mock_sm}[service]

        mock_boto.client.side_effect = pick
        result = universal_factory("secret_manager", "aws", {
            "aws_access_key_id": "k",
            "aws_secret_access_key": "s",
            "region_name": "us-east-1",
        })
        assert isinstance(result, SecretManagerBlueprint)

    @patch("cloud.aws.storage.boto3")
    def test_aws_storage(self, mock_boto):
        mock_boto.client.return_value = MagicMock()
        result = universal_factory("storage", "aws", {
            "aws_access_key_id": "k",
            "aws_secret_access_key": "s",
            "region_name": "us-east-1",
        })
        assert isinstance(result, CloudStorageBlueprint)

    @patch("cloud.gcp.secret_manager.secretmanager_v1")
    def test_gcp_secret_manager(self, mock_sm):
        mock_sm.SecretManagerServiceClient.return_value = MagicMock()
        result = universal_factory("secret_manager", "gcp", {"project_id": "p"})
        assert isinstance(result, SecretManagerBlueprint)

    @patch("cloud.gcp.storage.gcs")
    def test_gcp_storage(self, mock_gcs):
        mock_gcs.Client.return_value = MagicMock()
        result = universal_factory("storage", "gcp", {"project_id": "p"})
        assert isinstance(result, CloudStorageBlueprint)

    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Unsupported cloud provider"):
            universal_factory("secret_manager", "azure", {})

    def test_unsupported_service(self):
        with pytest.raises(ValueError, match="Unsupported service"):
            universal_factory("database", "aws", {})
