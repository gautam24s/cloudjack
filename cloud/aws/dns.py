"""AWS Route 53 implementation of the DNS blueprint."""

from __future__ import annotations

import uuid
from typing import Any, NoReturn

import boto3
from botocore.exceptions import ClientError

from cloud.base.dns import DNSBlueprint
from cloud.base.exceptions import (
    DNSError,
    ZoneNotFoundError,
    ZoneAlreadyExistsError,
)
from cloud.base.config import AWSConfig

_ERROR_MAP: dict[str, type[DNSError]] = {
    "NoSuchHostedZone": ZoneNotFoundError,
    "HostedZoneAlreadyExists": ZoneAlreadyExistsError,
}


def _handle(e: ClientError, msg: str) -> NoReturn:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or DNSError)(msg) from e


class DNS(DNSBlueprint):
    """AWS Route 53 DNS service.

    Attributes:
        client: boto3 Route 53 client.
    """

    def __init__(self, config: AWSConfig) -> None:
        """Initialize the Route 53 client.

        Args:
            config: AWS configuration object containing credentials and region.
                   Expected attributes:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "route53",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )

    # --- Zone lifecycle ---

    def create_zone(self, zone_name: str, **kwargs: Any) -> str:
        """Create a Route 53 hosted zone.

        Returns:
            Hosted zone ID (without ``/hostedzone/`` prefix).
        """
        try:
            resp = self.client.create_hosted_zone(
                Name=zone_name,
                CallerReference=kwargs.get("caller_reference", uuid.uuid4().hex),
                HostedZoneConfig={
                    "Comment": kwargs.get("comment", ""),
                    "PrivateZone": kwargs.get("private", False),
                },
            )
            return resp["HostedZone"]["Id"].split("/")[-1]  # type: ignore[no-any-return]
        except ClientError as e:
            _handle(e, f"Failed to create zone '{zone_name}'")

    def delete_zone(self, zone_id: str) -> None:
        """Delete a Route 53 hosted zone.

        Args:
            zone_id: Hosted zone ID.

        Raises:
            ZoneNotFoundError: If the zone does not exist.
        """
        try:
            self.client.delete_hosted_zone(Id=zone_id)
        except ClientError as e:
            _handle(e, f"Failed to delete zone '{zone_id}'")

    def list_zones(self) -> list[dict[str, Any]]:
        """List all Route 53 hosted zones.

        Returns:
            List of dicts with ``zone_id``, ``name``, ``record_count``,
            ``private``.

        Raises:
            DNSError: On Route 53 API failure.
        """
        try:
            resp = self.client.list_hosted_zones()
            return [
                {
                    "zone_id": z["Id"].split("/")[-1],
                    "name": z["Name"],
                    "record_count": z.get("ResourceRecordSetCount", 0),
                    "private": z.get("Config", {}).get("PrivateZone", False),
                }
                for z in resp.get("HostedZones", [])
            ]
        except ClientError as e:
            _handle(e, "Failed to list zones")

    # --- Record management ---

    def _change_record(
        self,
        zone_id: str,
        action: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int,
    ) -> None:
        """Apply a Route 53 change batch (UPSERT / DELETE).

        Args:
            zone_id: Hosted zone ID.
            action: Route 53 action (``UPSERT``, ``CREATE``, ``DELETE``).
            record_name: FQDN of the record.
            record_type: DNS record type (A, CNAME, MX, …).
            values: Record values.
            ttl: Time-to-live in seconds.

        Raises:
            DNSError: On Route 53 API failure.
        """
        try:
            self.client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    "Changes": [
                        {
                            "Action": action,
                            "ResourceRecordSet": {
                                "Name": record_name,
                                "Type": record_type,
                                "TTL": ttl,
                                "ResourceRecords": [
                                    {"Value": v} for v in values
                                ],
                            },
                        }
                    ]
                },
            )
        except ClientError as e:
            _handle(
                e,
                f"Failed to {action.lower()} record '{record_name}' in zone '{zone_id}'",
            )

    def create_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
        **kwargs: Any,
    ) -> None:
        """Create or upsert a DNS record in Route 53.

        Args:
            zone_id: Hosted zone ID.
            record_name: FQDN (e.g. ``www.example.com.``).
            record_type: Record type (A, CNAME, MX, …).
            values: List of record values.
            ttl: Time-to-live in seconds.
            **kwargs: ``action`` — override the change-batch action
                (default ``UPSERT``).
        """
        action = kwargs.get("action", "UPSERT")
        self._change_record(zone_id, action, record_name, record_type, values, ttl)

    def delete_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
    ) -> None:
        """Delete a DNS record from Route 53.

        Args:
            zone_id: Hosted zone ID.
            record_name: FQDN of the record to delete.
            record_type: Record type.
            values: Values that must match the existing record.
            ttl: TTL that must match the existing record.
        """
        self._change_record(zone_id, "DELETE", record_name, record_type, values, ttl)

    def list_records(self, zone_id: str) -> list[dict[str, Any]]:
        """List all DNS records in a Route 53 hosted zone.

        Args:
            zone_id: Hosted zone ID.

        Returns:
            List of dicts with ``name``, ``type``, ``ttl``, ``values``.

        Raises:
            DNSError: On Route 53 API failure.
        """
        try:
            resp = self.client.list_resource_record_sets(HostedZoneId=zone_id)
            return [
                {
                    "name": r["Name"],
                    "type": r["Type"],
                    "ttl": r.get("TTL", 0),
                    "values": [rr["Value"] for rr in r.get("ResourceRecords", [])],
                }
                for r in resp.get("ResourceRecordSets", [])
            ]
        except ClientError as e:
            _handle(e, f"Failed to list records in zone '{zone_id}'")
