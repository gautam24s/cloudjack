"""GCP Cloud Logging implementation of the Logging blueprint."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exceptions
from google.cloud import logging as cloud_logging

from cloud.base.logging_service import LoggingBlueprint
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    LoggingError,
    LogGroupNotFoundError,
    LogGroupAlreadyExistsError,
)


class Logging(LoggingBlueprint):
    """GCP Cloud Logging service.

    GCP Cloud Logging uses *loggers* (similar to log groups) identified
    by a log name.

    Attributes:
        client: Cloud Logging client.
        project_id: GCP project ID.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize the Cloud Logging client.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        self.project_id: str = config.project_id
        self.client = cloud_logging.Client(project=self.project_id, credentials=config.credentials)

    # --- Log group lifecycle ---

    def create_log_group(self, name: str, **kwargs: Any) -> None:
        """Create a Cloud Logging sink.

        In GCP, loggers are created implicitly; this creates a logging
        *sink* for export or retention purposes.  If no ``destination``
        kwarg is provided, the call is a no-op (the logger is auto-created
        on first write).
        """
        destination = kwargs.get("destination")
        if not destination:
            # GCP auto-creates loggers; nothing to do
            return
        try:
            self.client.sink(name, destination=destination).create()
        except gcp_exceptions.Conflict as e:
            raise LogGroupAlreadyExistsError(
                f"Sink '{name}' already exists"
            ) from e
        except Exception as e:
            raise LoggingError(f"Failed to create sink '{name}'") from e

    def delete_log_group(self, name: str) -> None:
        """Delete a log (all entries) or a sink."""
        try:
            logger = self.client.logger(name)
            logger.delete()
        except gcp_exceptions.NotFound as e:
            raise LogGroupNotFoundError(f"Log '{name}' not found") from e
        except Exception as e:
            raise LoggingError(f"Failed to delete log '{name}'") from e

    def list_log_groups(self, prefix: str = "") -> list[str]:
        try:
            entries = self.client.list_entries(
                filter_=f'logName:"{prefix}"' if prefix else None,
                page_size=0,
            )
            # Collect unique log names
            seen: set[str] = set()
            for entry in entries:
                log_name = entry.log_name.split("/")[-1] if entry.log_name else ""
                if log_name:
                    seen.add(log_name)
                if len(seen) > 500:
                    break
            return sorted(seen)
        except Exception as e:
            raise LoggingError("Failed to list log groups") from e

    # --- Log operations ---

    _SEVERITY_MAP = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def write_log(
        self,
        log_group: str,
        message: str,
        *,
        severity: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Write a log entry to Cloud Logging.

        Args:
            log_group: Logger name.
            message: Log message text.
            severity: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            **kwargs: ``labels`` — dict of key-value labels.

        Raises:
            LoggingError: On Cloud Logging API failure.
        """
        try:
            logger = self.client.logger(log_group)
            gcp_severity = self._SEVERITY_MAP.get(severity.upper(), "DEFAULT")
            labels = kwargs.get("labels", {})
            logger.log_text(message, severity=gcp_severity, labels=labels)
        except Exception as e:
            raise LoggingError(f"Failed to write log to '{log_group}'") from e

    def read_logs(
        self,
        log_group: str,
        *,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Read log entries from Cloud Logging.

        Args:
            log_group: Logger name to read from.
            limit: Maximum entries to return.
            **kwargs: ``filter_pattern`` — additional Cloud Logging filter string.

        Returns:
            List of dicts with ``timestamp``, ``message``, ``severity``.

        Raises:
            LoggingError: On Cloud Logging API failure.
        """
        try:
            filter_str = f'logName="projects/{self.project_id}/logs/{log_group}"'
            if "filter_pattern" in kwargs:
                filter_str += f" AND {kwargs['filter_pattern']}"
            entries = self.client.list_entries(
                filter_=filter_str,
                page_size=limit,
            )
            results: list[dict[str, Any]] = []
            for entry in entries:
                results.append(
                    {
                        "timestamp": str(entry.timestamp) if entry.timestamp else "",
                        "message": entry.payload if isinstance(entry.payload, str) else str(entry.payload),
                        "severity": entry.severity or "DEFAULT",
                    }
                )
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            raise LoggingError(f"Failed to read logs from '{log_group}'") from e
