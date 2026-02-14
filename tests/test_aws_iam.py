"""Tests for AWS IAM service."""

from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.iam import IAM
from cloud.base.exceptions import (
    IAMError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
)


def _client_error(code: str, msg: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, "op")


TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


@pytest.fixture
def svc():
    with patch("cloud.aws.iam.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = IAM({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1",
        })
        yield instance, mock_client


# --- create_role ---

class TestCreateRole:
    def test_success(self, svc):
        inst, client = svc
        client.create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123:role/test"}
        }
        arn = inst.create_role("test", TRUST_POLICY)
        assert arn == "arn:aws:iam::123:role/test"

    def test_with_description(self, svc):
        inst, client = svc
        client.create_role.return_value = {"Role": {"Arn": "arn"}}
        inst.create_role("test", TRUST_POLICY, description="My role")
        call_kwargs = client.create_role.call_args[1]
        assert call_kwargs["Description"] == "My role"

    def test_already_exists(self, svc):
        inst, client = svc
        client.create_role.side_effect = _client_error("EntityAlreadyExists")
        with pytest.raises(RoleAlreadyExistsError):
            inst.create_role("dup", TRUST_POLICY)

    def test_generic_error(self, svc):
        inst, client = svc
        client.create_role.side_effect = _client_error("ServiceFailure")
        with pytest.raises(IAMError):
            inst.create_role("fail", TRUST_POLICY)


# --- delete_role ---

class TestDeleteRole:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_role("test")
        client.delete_role.assert_called_once_with(RoleName="test")

    def test_not_found(self, svc):
        inst, client = svc
        client.delete_role.side_effect = _client_error("NoSuchEntity")
        with pytest.raises(RoleNotFoundError):
            inst.delete_role("missing")


# --- list_roles ---

class TestListRoles:
    def test_success(self, svc):
        inst, client = svc
        client.list_roles.return_value = {
            "Roles": [
                {
                    "RoleName": "admin",
                    "RoleId": "AROA123",
                    "Arn": "arn:aws:iam::123:role/admin",
                    "CreateDate": "2024-01-01",
                }
            ]
        }
        roles = inst.list_roles()
        assert len(roles) == 1
        assert roles[0]["role_name"] == "admin"

    def test_empty(self, svc):
        inst, client = svc
        client.list_roles.return_value = {"Roles": []}
        assert inst.list_roles() == []


# --- attach_policy ---

class TestAttachPolicy:
    def test_success(self, svc):
        inst, client = svc
        inst.attach_policy("admin", "arn:aws:iam::aws:policy/ReadOnly")
        client.attach_role_policy.assert_called_once_with(
            RoleName="admin",
            PolicyArn="arn:aws:iam::aws:policy/ReadOnly",
        )

    def test_not_found(self, svc):
        inst, client = svc
        client.attach_role_policy.side_effect = _client_error("NoSuchEntity")
        with pytest.raises(RoleNotFoundError):
            inst.attach_policy("missing", "arn")


# --- detach_policy ---

class TestDetachPolicy:
    def test_success(self, svc):
        inst, client = svc
        inst.detach_policy("admin", "arn:aws:iam::aws:policy/ReadOnly")
        client.detach_role_policy.assert_called_once()

    def test_not_found(self, svc):
        inst, client = svc
        client.detach_role_policy.side_effect = _client_error("NoSuchEntity")
        with pytest.raises(RoleNotFoundError):
            inst.detach_policy("missing", "arn")


# --- list_policies ---

class TestListPolicies:
    def test_success(self, svc):
        inst, client = svc
        client.list_policies.return_value = {
            "Policies": [
                {
                    "PolicyName": "MyPolicy",
                    "Arn": "arn:aws:iam::123:policy/MyPolicy",
                    "CreateDate": "2024-01-01",
                }
            ]
        }
        policies = inst.list_policies()
        assert len(policies) == 1
        assert policies[0]["policy_name"] == "MyPolicy"

    def test_empty(self, svc):
        inst, client = svc
        client.list_policies.return_value = {"Policies": []}
        assert inst.list_policies() == []
