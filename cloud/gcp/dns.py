"""GCP Cloud DNS implementation of the DNS blueprint."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exceptions
from google.cloud import dns as cloud_dns  # type: ignore[attr-defined]

from cloud.base.dns import DNSBlueprint
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    DNSError,
    ZoneNotFoundError,
    ZoneAlreadyExistsError,
)


class DNS(DNSBlueprint):
    """GCP Cloud DNS service.

    Attributes:
        client: Cloud DNS client.
        project_id: GCP project ID.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize the Cloud DNS client.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        assert config.project_id is not None  # guaranteed by GCPConfig validator
        self.project_id: str = config.project_id
        self.client = cloud_dns.Client(project=self.project_id, credentials=config.credentials)

    # --- Zone lifecycle ---

    def create_zone(self, zone_name: str, **kwargs: Any) -> str:
        """Create a Cloud DNS managed zone.

        Args:
            zone_name: FQDN (e.g. ``example.com.``).
            **kwargs: ``dns_name`` (defaults to *zone_name*), ``description``.

        Returns:
            Zone name identifier.
        """
        try:
            # Cloud DNS zone names are identifiers, not FQDNs
            safe_name = zone_name.rstrip(".").replace(".", "-")
            dns_name = kwargs.get("dns_name", zone_name)
            zone = self.client.zone(
                safe_name,
                dns_name=dns_name,
                description=kwargs.get("description", ""),
            )
            zone.create()
            return safe_name
        except gcp_exceptions.Conflict as e:
            raise ZoneAlreadyExistsError(
                f"Zone '{zone_name}' already exists"
            ) from e
        except Exception as e:
            raise DNSError(f"Failed to create zone '{zone_name}'") from e

    def delete_zone(self, zone_id: str) -> None:
        """Delete a Cloud DNS managed zone.

        Args:
            zone_id: Zone name identifier.

        Raises:
            ZoneNotFoundError: If the zone does not exist.
        """
        try:
            zone = self.client.zone(zone_id)
            zone.delete()
        except gcp_exceptions.NotFound as e:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found") from e
        except Exception as e:
            raise DNSError(f"Failed to delete zone '{zone_id}'") from e

    def list_zones(self) -> list[dict[str, Any]]:
        """List all Cloud DNS managed zones.

        Returns:
            List of dicts with ``zone_id``, ``name``, ``description``.

        Raises:
            DNSError: On Cloud DNS API failure.
        """
        try:
            zones = self.client.list_zones()
            return [
                {
                    "zone_id": z.name,
                    "name": z.dns_name,
                    "description": z.description,
                }
                for z in zones
            ]
        except Exception as e:
            raise DNSError("Failed to list zones") from e

    # --- Record management ---

    def create_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
        **kwargs: Any,
    ) -> None:
        """Create a DNS record in a Cloud DNS zone.

        Args:
            zone_id: Zone name identifier.
            record_name: FQDN (e.g. ``www.example.com.``).
            record_type: Record type (A, CNAME, MX, …).
            values: List of record values.
            ttl: Time-to-live in seconds.

        Raises:
            ZoneNotFoundError: If the zone does not exist.
            DNSError: On API failure.
        """
        try:
            zone = self.client.zone(zone_id)
            changes = zone.changes()
            record = zone.resource_record_set(
                record_name, record_type, ttl, values
            )
            changes.add_record_set(record)
            changes.create()
        except gcp_exceptions.NotFound as e:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found") from e
        except Exception as e:
            raise DNSError(
                f"Failed to create record '{record_name}' in '{zone_id}'"
            ) from e

    def delete_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
    ) -> None:
        """Delete a DNS record from a Cloud DNS zone.

        Args:
            zone_id: Zone name identifier.
            record_name: FQDN of the record.
            record_type: Record type.
            values: Values that must match the record.
            ttl: TTL that must match the record.

        Raises:
            ZoneNotFoundError: If the zone does not exist.
            DNSError: On API failure.
        """
        try:
            zone = self.client.zone(zone_id)
            changes = zone.changes()
            record = zone.resource_record_set(
                record_name, record_type, ttl, values
            )
            changes.delete_record_set(record)
            changes.create()
        except gcp_exceptions.NotFound as e:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found") from e
        except Exception as e:
            raise DNSError(
                f"Failed to delete record '{record_name}' from '{zone_id}'"
            ) from e

    def list_records(self, zone_id: str) -> list[dict[str, Any]]:
        """List all DNS records in a Cloud DNS zone.

        Args:
            zone_id: Zone name identifier.

        Returns:
            List of dicts with ``name``, ``type``, ``ttl``, ``values``.

        Raises:
            ZoneNotFoundError: If the zone does not exist.
        """
        try:
            zone = self.client.zone(zone_id)
            records = zone.list_resource_record_sets()
            return [
                {
                    "name": r.name,
                    "type": r.record_type,
                    "ttl": r.ttl,
                    "values": list(r.rrdatas),
                }
                for r in records
            ]
        except gcp_exceptions.NotFound as e:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found") from e
        except Exception as e:
            raise DNSError(f"Failed to list records in '{zone_id}'") from e
