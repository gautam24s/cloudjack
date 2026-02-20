"""Tests for GCP Compute Engine service."""

from unittest.mock import patch, MagicMock
import pytest

from google.api_core import exceptions as gcp_exceptions

from cloud.gcp.compute import Compute
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    ComputeError,
    InstanceNotFoundError,
    InstanceAlreadyExistsError,
)


@pytest.fixture
def svc():
    with (
        patch("cloud.gcp.compute.compute_v1.InstancesClient") as MockInstances,
        patch("cloud.gcp.compute.compute_v1.ZoneOperationsClient") as MockOps,
    ):
        mock_instances = MockInstances.return_value
        mock_ops = MockOps.return_value
        instance = Compute(GCPConfig(project_id="my-project"))
        yield instance, mock_instances, mock_ops


# --- create_instance ---

class TestCreateInstance:
    def test_success(self, svc):
        inst, client, ops = svc
        mock_op = MagicMock()
        mock_op.name = "op-123"
        client.insert.return_value = mock_op
        result = inst.create_instance(
            "web", "e2-micro",
            "projects/debian-cloud/global/images/family/debian-12"
        )
        assert result == "web"
        client.insert.assert_called_once()
        ops.wait.assert_called_once()

    def test_already_exists(self, svc):
        inst, client, ops = svc
        client.insert.side_effect = gcp_exceptions.AlreadyExists("exists")
        with pytest.raises(InstanceAlreadyExistsError):
            inst.create_instance("dup", "e2-micro", "img")

    def test_generic_error(self, svc):
        inst, client, ops = svc
        client.insert.side_effect = gcp_exceptions.InternalServerError("fail")
        with pytest.raises(ComputeError):
            inst.create_instance("fail", "e2-micro", "img")


# --- start / stop / terminate ---

class TestLifecycle:
    def test_start(self, svc):
        inst, client, ops = svc
        mock_op = MagicMock()
        mock_op.name = "op"
        client.start.return_value = mock_op
        inst.start_instance("web")
        client.start.assert_called_once()

    def test_stop(self, svc):
        inst, client, ops = svc
        mock_op = MagicMock()
        mock_op.name = "op"
        client.stop.return_value = mock_op
        inst.stop_instance("web")
        client.stop.assert_called_once()

    def test_terminate(self, svc):
        inst, client, ops = svc
        mock_op = MagicMock()
        mock_op.name = "op"
        client.delete.return_value = mock_op
        inst.terminate_instance("web")
        client.delete.assert_called_once()

    def test_start_not_found(self, svc):
        inst, client, ops = svc
        client.start.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(InstanceNotFoundError):
            inst.start_instance("missing")

    def test_stop_not_found(self, svc):
        inst, client, ops = svc
        client.stop.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(InstanceNotFoundError):
            inst.stop_instance("missing")

    def test_terminate_not_found(self, svc):
        inst, client, ops = svc
        client.delete.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(InstanceNotFoundError):
            inst.terminate_instance("missing")


# --- list_instances ---

class TestListInstances:
    def test_success(self, svc):
        inst, client, ops = svc
        mock_inst = MagicMock()
        mock_inst.name = "web"
        mock_inst.status = "RUNNING"
        mock_inst.machine_type = "zones/us-central1-a/machineTypes/e2-micro"
        mock_inst.creation_timestamp = "2024-01-01"
        client.list.return_value = [mock_inst]
        result = inst.list_instances()
        assert len(result) == 1
        assert result[0]["name"] == "web"
        assert result[0]["state"] == "RUNNING"
        assert result[0]["instance_type"] == "e2-micro"

    def test_empty(self, svc):
        inst, client, ops = svc
        client.list.return_value = []
        assert inst.list_instances() == []


# --- get_instance ---

class TestGetInstance:
    def test_success(self, svc):
        inst, client, ops = svc
        mock_inst = MagicMock()
        mock_inst.name = "web"
        mock_inst.status = "RUNNING"
        mock_inst.machine_type = "zones/z/machineTypes/e2-micro"
        mock_inst.creation_timestamp = "2024-01-01"
        mock_iface = MagicMock()
        mock_iface.network_i_p = "10.0.0.1"
        mock_ac = MagicMock()
        mock_ac.nat_i_p = "35.1.2.3"
        mock_iface.access_configs = [mock_ac]
        mock_inst.network_interfaces = [mock_iface]
        client.get.return_value = mock_inst
        result = inst.get_instance("web")
        assert result["public_ip"] == "35.1.2.3"
        assert result["private_ip"] == "10.0.0.1"

    def test_not_found(self, svc):
        inst, client, ops = svc
        client.get.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(InstanceNotFoundError):
            inst.get_instance("missing")
