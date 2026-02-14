"""Tests for AWS EC2 Compute service."""

from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.compute import Compute
from cloud.base.exceptions import ComputeError, InstanceNotFoundError


def _client_error(code: str, msg: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, "op")


@pytest.fixture
def svc():
    with patch("cloud.aws.compute.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = Compute({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1",
        })
        yield instance, mock_client


# --- create_instance ---

class TestCreateInstance:
    def test_success(self, svc):
        inst, client = svc
        client.run_instances.return_value = {
            "Instances": [{"InstanceId": "i-abc123"}]
        }
        iid = inst.create_instance("web", "t3.micro", "ami-123")
        assert iid == "i-abc123"

    def test_with_kwargs(self, svc):
        inst, client = svc
        client.run_instances.return_value = {
            "Instances": [{"InstanceId": "i-xyz"}]
        }
        inst.create_instance("web", "t3.micro", "ami-123", key_name="mykey", subnet_id="subnet-1")
        call_kwargs = client.run_instances.call_args[1]
        assert call_kwargs["KeyName"] == "mykey"
        assert call_kwargs["SubnetId"] == "subnet-1"

    def test_error(self, svc):
        inst, client = svc
        client.run_instances.side_effect = _client_error("InsufficientInstanceCapacity")
        with pytest.raises(ComputeError):
            inst.create_instance("web", "t3.micro", "ami-123")


# --- start / stop / terminate ---

class TestInstanceLifecycle:
    def test_start_success(self, svc):
        inst, client = svc
        inst.start_instance("i-abc")
        client.start_instances.assert_called_once_with(InstanceIds=["i-abc"])

    def test_stop_success(self, svc):
        inst, client = svc
        inst.stop_instance("i-abc")
        client.stop_instances.assert_called_once_with(InstanceIds=["i-abc"])

    def test_terminate_success(self, svc):
        inst, client = svc
        inst.terminate_instance("i-abc")
        client.terminate_instances.assert_called_once_with(InstanceIds=["i-abc"])

    def test_start_not_found(self, svc):
        inst, client = svc
        client.start_instances.side_effect = _client_error("InvalidInstanceID.NotFound")
        with pytest.raises(InstanceNotFoundError):
            inst.start_instance("i-missing")

    def test_stop_not_found(self, svc):
        inst, client = svc
        client.stop_instances.side_effect = _client_error("InvalidInstanceID.NotFound")
        with pytest.raises(InstanceNotFoundError):
            inst.stop_instance("i-missing")

    def test_terminate_generic(self, svc):
        inst, client = svc
        client.terminate_instances.side_effect = _client_error("UnauthorizedAccess")
        with pytest.raises(ComputeError):
            inst.terminate_instance("i-abc")


# --- list_instances ---

class TestListInstances:
    def test_success(self, svc):
        inst, client = svc
        client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1",
                            "State": {"Name": "running"},
                            "InstanceType": "t3.micro",
                            "Tags": [{"Key": "Name", "Value": "web"}],
                            "LaunchTime": "2024-01-01T00:00:00Z",
                        }
                    ]
                }
            ]
        }
        result = inst.list_instances()
        assert len(result) == 1
        assert result[0]["instance_id"] == "i-1"
        assert result[0]["name"] == "web"
        assert result[0]["state"] == "running"

    def test_empty(self, svc):
        inst, client = svc
        client.describe_instances.return_value = {"Reservations": []}
        assert inst.list_instances() == []

    def test_no_tags(self, svc):
        inst, client = svc
        client.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [{"InstanceId": "i-1", "State": {"Name": "running"}}]}
            ]
        }
        result = inst.list_instances()
        assert result[0]["name"] == ""


# --- get_instance ---

class TestGetInstance:
    def test_success(self, svc):
        inst, client = svc
        client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1",
                            "State": {"Name": "running"},
                            "InstanceType": "t3.micro",
                            "Tags": [{"Key": "Name", "Value": "web"}],
                            "LaunchTime": "2024-01-01",
                            "PublicIpAddress": "1.2.3.4",
                            "PrivateIpAddress": "10.0.0.1",
                        }
                    ]
                }
            ]
        }
        result = inst.get_instance("i-1")
        assert result["public_ip"] == "1.2.3.4"
        assert result["private_ip"] == "10.0.0.1"

    def test_not_found(self, svc):
        inst, client = svc
        client.describe_instances.side_effect = _client_error("InvalidInstanceID.NotFound")
        with pytest.raises(InstanceNotFoundError):
            inst.get_instance("i-missing")
