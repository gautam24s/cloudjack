"""Tests for GCP Cloud DNS service."""

from unittest.mock import patch, MagicMock
import pytest

from google.api_core import exceptions as gcp_exceptions

from cloud.gcp.dns import DNS
from cloud.base.exceptions import DNSError, ZoneNotFoundError, ZoneAlreadyExistsError


@pytest.fixture
def svc():
    with patch("cloud.gcp.dns.cloud_dns.Client") as MockClient:
        mock_client = MockClient.return_value
        instance = DNS({"project_id": "my-project"})
        yield instance, mock_client


# --- create_zone ---

class TestCreateZone:
    def test_success(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        client.zone.return_value = mock_zone
        zid = inst.create_zone("example.com.")
        assert zid == "example-com"
        mock_zone.create.assert_called_once()

    def test_already_exists(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_zone.create.side_effect = gcp_exceptions.Conflict("exists")
        client.zone.return_value = mock_zone
        with pytest.raises(ZoneAlreadyExistsError):
            inst.create_zone("dup.com.")

    def test_generic_error(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_zone.create.side_effect = Exception("fail")
        client.zone.return_value = mock_zone
        with pytest.raises(DNSError):
            inst.create_zone("fail.com.")


# --- delete_zone ---

class TestDeleteZone:
    def test_success(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        client.zone.return_value = mock_zone
        inst.delete_zone("example-com")
        mock_zone.delete.assert_called_once()

    def test_not_found(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_zone.delete.side_effect = gcp_exceptions.NotFound("nope")
        client.zone.return_value = mock_zone
        with pytest.raises(ZoneNotFoundError):
            inst.delete_zone("missing")


# --- list_zones ---

class TestListZones:
    def test_success(self, svc):
        inst, client = svc
        mock_z = MagicMock()
        mock_z.name = "example-com"
        mock_z.dns_name = "example.com."
        mock_z.description = ""
        client.list_zones.return_value = [mock_z]
        zones = inst.list_zones()
        assert len(zones) == 1
        assert zones[0]["zone_id"] == "example-com"

    def test_empty(self, svc):
        inst, client = svc
        client.list_zones.return_value = []
        assert inst.list_zones() == []


# --- create_record ---

class TestCreateRecord:
    def test_success(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_changes = MagicMock()
        mock_zone.changes.return_value = mock_changes
        mock_zone.resource_record_set.return_value = "record"
        client.zone.return_value = mock_zone
        inst.create_record("example-com", "www.example.com.", "A", ["1.2.3.4"])
        mock_changes.add_record_set.assert_called_once_with("record")
        mock_changes.create.assert_called_once()

    def test_zone_not_found(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_changes = MagicMock()
        mock_changes.create.side_effect = gcp_exceptions.NotFound("nope")
        mock_zone.changes.return_value = mock_changes
        mock_zone.resource_record_set.return_value = "r"
        client.zone.return_value = mock_zone
        with pytest.raises(ZoneNotFoundError):
            inst.create_record("bad", "www.x.com.", "A", ["1.2.3.4"])


# --- delete_record ---

class TestDeleteRecord:
    def test_success(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_changes = MagicMock()
        mock_zone.changes.return_value = mock_changes
        mock_zone.resource_record_set.return_value = "record"
        client.zone.return_value = mock_zone
        inst.delete_record("z", "www.x.com.", "A", ["1.2.3.4"])
        mock_changes.delete_record_set.assert_called_once_with("record")
        mock_changes.create.assert_called_once()


# --- list_records ---

class TestListRecords:
    def test_success(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_record = MagicMock()
        mock_record.name = "example.com."
        mock_record.record_type = "NS"
        mock_record.ttl = 300
        mock_record.rrdatas = ["ns1.gcp.com."]
        mock_zone.list_resource_record_sets.return_value = [mock_record]
        client.zone.return_value = mock_zone
        records = inst.list_records("example-com")
        assert len(records) == 1
        assert records[0]["type"] == "NS"

    def test_not_found(self, svc):
        inst, client = svc
        mock_zone = MagicMock()
        mock_zone.list_resource_record_sets.side_effect = gcp_exceptions.NotFound("nope")
        client.zone.return_value = mock_zone
        with pytest.raises(ZoneNotFoundError):
            inst.list_records("missing")
