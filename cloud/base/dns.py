"""DNS service blueprint."""

from abc import ABC, abstractmethod
from typing import Any


class DNSBlueprint(ABC):
    """Abstract interface for DNS zone and record management.

    Maps to AWS Route 53 and GCP Cloud DNS.
    """

    # --- Zone lifecycle ---

    @abstractmethod
    def create_zone(self, zone_name: str, **kwargs: Any) -> str:
        """Create a hosted zone and return its identifier.

        Args:
            zone_name: Fully qualified domain (e.g. ``example.com.``).

        Keyword Args:
            caller_reference (str): Unique string to identify the request,
                auto-generated UUID if omitted *(AWS)*.
            comment (str): Zone description *(AWS)*.
            private (bool): Whether to create a private hosted zone *(AWS)*.
            description (str): Zone description *(GCP)*.
            visibility (str): ``"public"`` or ``"private"``,
                default ``"public"`` *(GCP)*.
            dns_name (str): Override the DNS name, defaults to
                *zone_name* *(GCP)*.

        Returns:
            Zone identifier.
        """

    @abstractmethod
    def delete_zone(self, zone_id: str) -> None:
        """Delete a hosted zone."""

    @abstractmethod
    def list_zones(self) -> list[dict[str, Any]]:
        """List hosted zones.

        Each dict contains at least ``zone_id`` and ``name``.
        """

    # --- Record management ---

    @abstractmethod
    def create_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
        **kwargs: Any,
    ) -> None:
        """Create or upsert a DNS record.

        Args:
            zone_id: Zone identifier.
            record_name: FQDN of the record (e.g. ``www.example.com.``).
            record_type: Record type (A, AAAA, CNAME, MX, TXT, …).
            values: List of record values.
            ttl: Time-to-live in seconds.

        Keyword Args:
            action (str): Change-batch action — ``UPSERT``, ``CREATE``,
                or ``DELETE``, default ``UPSERT`` *(AWS)*.
        """

    @abstractmethod
    def delete_record(
        self,
        zone_id: str,
        record_name: str,
        record_type: str,
        values: list[str],
        ttl: int = 300,
    ) -> None:
        """Delete a DNS record.

        Args:
            zone_id: Zone identifier.
            record_name: FQDN of the record.
            record_type: Record type.
            values: Values that must match the record to delete.
            ttl: Time-to-live (required by some providers for exact match).
        """

    @abstractmethod
    def list_records(self, zone_id: str) -> list[dict[str, Any]]:
        """List records in a zone.

        Each dict contains at least ``name``, ``type``, ``ttl``, ``values``.
        """
