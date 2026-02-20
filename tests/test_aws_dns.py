"""Tests for AWS Route 53 DNS service."""

from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.dns import DNS
from cloud.base.config import AWSConfig
from cloud.base.exceptions import DNSError, ZoneNotFoundError, ZoneAlreadyExistsError


def _client_error(code: str, msg: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, "op")


@pytest.fixture
def svc():
    with patch("cloud.aws.dns.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = DNS(AWSConfig(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            region_name="us-east-1",
        ))
        yield instance, mock_client


# --- create_zone ---

class TestCreateZone:
    def test_success(self, svc):
        inst, client = svc
        client.create_hosted_zone.return_value = {
            "HostedZone": {"Id": "/hostedzone/Z123"}
        }
        zid = inst.create_zone("example.com.")
        assert zid == "Z123"

    def test_already_exists(self, svc):
        inst, client = svc
        client.create_hosted_zone.side_effect = _client_error("HostedZoneAlreadyExists")
        with pytest.raises(ZoneAlreadyExistsError):
            inst.create_zone("dup.com.")

    def test_generic_error(self, svc):
        inst, client = svc
        client.create_hosted_zone.side_effect = _client_error("DelegationSetNotAvailable")
        with pytest.raises(DNSError):
            inst.create_zone("fail.com.")


# --- delete_zone ---

class TestDeleteZone:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_zone("Z123")
        client.delete_hosted_zone.assert_called_once_with(Id="Z123")

    def test_not_found(self, svc):
        inst, client = svc
        client.delete_hosted_zone.side_effect = _client_error("NoSuchHostedZone")
        with pytest.raises(ZoneNotFoundError):
            inst.delete_zone("Z-missing")


# --- list_zones ---

class TestListZones:
    def test_success(self, svc):
        inst, client = svc
        client.list_hosted_zones.return_value = {
            "HostedZones": [
                {
                    "Id": "/hostedzone/Z1",
                    "Name": "example.com.",
                    "ResourceRecordSetCount": 5,
                    "Config": {"PrivateZone": False},
                }
            ]
        }
        zones = inst.list_zones()
        assert len(zones) == 1
        assert zones[0]["zone_id"] == "Z1"
        assert zones[0]["name"] == "example.com."

    def test_empty(self, svc):
        inst, client = svc
        client.list_hosted_zones.return_value = {"HostedZones": []}
        assert inst.list_zones() == []


# --- create_record ---

class TestCreateRecord:
    def test_success(self, svc):
        inst, client = svc
        inst.create_record("Z1", "www.example.com.", "A", ["1.2.3.4"])
        client.change_resource_record_sets.assert_called_once()
        args = client.change_resource_record_sets.call_args[1]
        change = args["ChangeBatch"]["Changes"][0]
        assert change["Action"] == "UPSERT"
        assert change["ResourceRecordSet"]["Name"] == "www.example.com."

    def test_error(self, svc):
        inst, client = svc
        client.change_resource_record_sets.side_effect = _client_error("NoSuchHostedZone")
        with pytest.raises(ZoneNotFoundError):
            inst.create_record("Z-bad", "www.x.com.", "A", ["1.2.3.4"])


# --- delete_record ---

class TestDeleteRecord:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_record("Z1", "www.example.com.", "A", ["1.2.3.4"])
        args = client.change_resource_record_sets.call_args[1]
        assert args["ChangeBatch"]["Changes"][0]["Action"] == "DELETE"


# --- list_records ---

class TestListRecords:
    def test_success(self, svc):
        inst, client = svc
        client.list_resource_record_sets.return_value = {
            "ResourceRecordSets": [
                {
                    "Name": "example.com.",
                    "Type": "NS",
                    "TTL": 172800,
                    "ResourceRecords": [{"Value": "ns1.aws.com."}],
                }
            ]
        }
        records = inst.list_records("Z1")
        assert len(records) == 1
        assert records[0]["type"] == "NS"
        assert records[0]["values"] == ["ns1.aws.com."]

    def test_not_found(self, svc):
        inst, client = svc
        client.list_resource_record_sets.side_effect = _client_error("NoSuchHostedZone")
        with pytest.raises(ZoneNotFoundError):
            inst.list_records("Z-missing")
