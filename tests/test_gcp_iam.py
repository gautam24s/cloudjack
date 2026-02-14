"""Tests for GCP IAM service."""

from unittest.mock import patch, MagicMock
import pytest

from google.api_core import exceptions as gcp_exceptions

from cloud.gcp.iam import IAM
from cloud.base.exceptions import (
    IAMError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
)


TRUST_POLICY = {
    "title": "Test Role",
    "description": "A test role",
    "permissions": ["storage.buckets.list", "storage.objects.get"],
    "stage": "GA",
}


@pytest.fixture
def svc():
    with patch("cloud.gcp.iam.iam_admin_v1.IAMClient") as MockClient:
        mock_client = MockClient.return_value
        instance = IAM({"project_id": "my-project"})
        yield instance, mock_client


# --- create_role ---

class TestCreateRole:
    def test_success(self, svc):
        inst, client = svc
        mock_resp = MagicMock()
        mock_resp.name = "projects/my-project/roles/TestRole"
        client.create_role.return_value = mock_resp
        result = inst.create_role("TestRole", TRUST_POLICY)
        assert result == "projects/my-project/roles/TestRole"

    def test_already_exists(self, svc):
        inst, client = svc
        client.create_role.side_effect = gcp_exceptions.AlreadyExists("exists")
        with pytest.raises(RoleAlreadyExistsError):
            inst.create_role("dup", TRUST_POLICY)

    def test_generic_error(self, svc):
        inst, client = svc
        client.create_role.side_effect = gcp_exceptions.InternalServerError("fail")
        with pytest.raises(IAMError):
            inst.create_role("fail", TRUST_POLICY)


# --- delete_role ---

class TestDeleteRole:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_role("TestRole")
        client.delete_role.assert_called_once()

    def test_full_path(self, svc):
        inst, client = svc
        inst.delete_role("projects/my-project/roles/TestRole")
        call_args = client.delete_role.call_args[1]
        assert call_args["request"]["name"] == "projects/my-project/roles/TestRole"

    def test_not_found(self, svc):
        inst, client = svc
        client.delete_role.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(RoleNotFoundError):
            inst.delete_role("missing")


# --- list_roles ---

class TestListRoles:
    def test_success(self, svc):
        inst, client = svc
        mock_role = MagicMock()
        mock_role.name = "projects/my-project/roles/viewer"
        mock_role.title = "Viewer"
        mock_role.description = "View only"
        client.list_roles.return_value = [mock_role]
        roles = inst.list_roles()
        assert len(roles) == 1
        assert roles[0]["role_name"] == "viewer"

    def test_empty(self, svc):
        inst, client = svc
        client.list_roles.return_value = []
        assert inst.list_roles() == []


# --- attach_policy / detach_policy ---

class TestPolicyBinding:
    def test_attach_existing_binding(self, svc):
        inst, client = svc
        mock_binding = MagicMock()
        mock_binding.role = "roles/viewer"
        mock_binding.members = ["user:bob@example.com"]
        mock_policy = MagicMock()
        mock_policy.bindings = [mock_binding]

        with patch.object(inst, "_get_policy", return_value=mock_policy):
            with patch.object(inst, "_set_policy") as mock_set:
                inst.attach_policy("roles/viewer", "user:alice@example.com")
                mock_set.assert_called_once()
                assert "user:alice@example.com" in mock_binding.members

    def test_attach_new_binding(self, svc):
        inst, client = svc
        mock_policy = MagicMock()
        mock_policy.bindings = []

        with patch.object(inst, "_get_policy", return_value=mock_policy):
            with patch.object(inst, "_set_policy") as mock_set:
                inst.attach_policy("roles/editor", "user:alice@example.com")
                mock_set.assert_called_once()

    def test_detach(self, svc):
        inst, client = svc
        mock_binding = MagicMock()
        mock_binding.role = "roles/viewer"
        mock_binding.members = ["user:alice@example.com"]
        mock_policy = MagicMock()
        mock_policy.bindings = [mock_binding]

        with patch.object(inst, "_get_policy", return_value=mock_policy):
            with patch.object(inst, "_set_policy") as mock_set:
                inst.detach_policy("roles/viewer", "user:alice@example.com")
                mock_set.assert_called_once()
                assert "user:alice@example.com" not in mock_binding.members

    def test_attach_error(self, svc):
        inst, client = svc
        with patch.object(inst, "_get_policy", side_effect=Exception("fail")):
            with pytest.raises(IAMError):
                inst.attach_policy("roles/viewer", "user:a@b.com")


# --- list_policies ---

class TestListPolicies:
    def test_success(self, svc):
        inst, client = svc
        mock_binding = MagicMock()
        mock_binding.role = "roles/viewer"
        mock_binding.members = ["user:a@b.com"]
        mock_policy = MagicMock()
        mock_policy.bindings = [mock_binding]

        with patch.object(inst, "_get_policy", return_value=mock_policy):
            policies = inst.list_policies()
            assert len(policies) == 1
            assert policies[0]["policy_name"] == "roles/viewer"

    def test_error(self, svc):
        inst, client = svc
        with patch.object(inst, "_get_policy", side_effect=Exception("fail")):
            with pytest.raises(IAMError):
                inst.list_policies()
