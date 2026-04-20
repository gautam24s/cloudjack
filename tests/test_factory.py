from unittest.mock import patch, MagicMock
import pytest

from cloudjack.factory import universal_factory
from cloudjack.base import SecretManagerService, StorageService
from cloudjack.base.config import AWSConfig, GCPConfig


class TestUniversalFactory:
    @patch("cloudjack.aws.secret_manager.boto3")
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
        assert isinstance(result, SecretManagerService)

    @patch("cloudjack.aws.storage.boto3")
    def test_aws_storage(self, mock_boto):
        mock_boto.client.return_value = MagicMock()
        result = universal_factory("storage", "aws", {
            "aws_access_key_id": "k",
            "aws_secret_access_key": "s",
            "region_name": "us-east-1",
        })
        assert isinstance(result, StorageService)

    @patch("cloudjack.gcp.secret_manager.secretmanager_v1")
    def test_gcp_secret_manager(self, mock_sm):
        mock_sm.SecretManagerServiceClient.return_value = MagicMock()
        result = universal_factory("secret_manager", "gcp", {"project_id": "p"})
        assert isinstance(result, SecretManagerService)

    @patch("cloudjack.gcp.storage.gcs")
    def test_gcp_storage(self, mock_gcs):
        mock_gcs.Client.return_value = MagicMock()
        result = universal_factory("storage", "gcp", {"project_id": "p"})
        assert isinstance(result, StorageService)

    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Unsupported cloud provider"):
            universal_factory("secret_manager", "azure", {})

    def test_unsupported_service(self):
        with pytest.raises(ValueError, match="Unsupported service"):
            universal_factory("database", "aws", {})

    @patch("cloudjack.aws.storage.boto3")
    def test_accepts_aws_config_instance(self, mock_boto):
        # A pre-built AWSConfig is accepted as-is (no re-validation / no
        # round-trip through a dict).
        mock_boto.client.return_value = MagicMock()
        cfg = AWSConfig(
            aws_access_key_id="k",
            aws_secret_access_key="s",
            region_name="us-east-1",
        )
        result = universal_factory("storage", "aws", cfg)
        assert isinstance(result, StorageService)

    @patch("cloudjack.gcp.storage.gcs")
    def test_accepts_gcp_config_instance(self, mock_gcs):
        mock_gcs.Client.return_value = MagicMock()
        cfg = GCPConfig(project_id="p")
        result = universal_factory("storage", "gcp", cfg)
        assert isinstance(result, StorageService)

    def test_rejects_mismatched_config_type(self):
        # Passing a GCPConfig for the AWS provider is a static mismatch; the
        # factory catches it at runtime too.
        cfg = GCPConfig(project_id="p")
        with pytest.raises(TypeError, match="AWSConfig"):
            universal_factory("storage", "aws", cfg)
