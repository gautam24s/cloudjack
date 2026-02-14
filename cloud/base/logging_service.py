"""Cloud logging service blueprint."""

from abc import ABC, abstractmethod
from typing import Any


class LoggingBlueprint(ABC):
    """Abstract interface for cloud log management.

    Maps to AWS CloudWatch Logs and GCP Cloud Logging.
    """

    # --- Log group lifecycle ---

    @abstractmethod
    def create_log_group(self, name: str, **kwargs: Any) -> None:
        """Create a log group / sink.

        Args:
            name: Log group name.
            **kwargs: Provider-specific options (retention, tags, …).
        """

    @abstractmethod
    def delete_log_group(self, name: str) -> None:
        """Delete a log group / sink."""

    @abstractmethod
    def list_log_groups(self, prefix: str = "") -> list[str]:
        """List log group names, optionally filtered by *prefix*."""

    # --- Log operations ---

    @abstractmethod
    def write_log(
        self,
        log_group: str,
        message: str,
        *,
        severity: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Write a log entry.

        Args:
            log_group: Target log group name.
            message: Log message string.
            severity: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            **kwargs: Provider-specific options (labels, stream name, …).
        """

    @abstractmethod
    def read_logs(
        self,
        log_group: str,
        *,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Read log entries.

        Each dict contains at least ``timestamp``, ``message``, ``severity``.

        Args:
            log_group: Log group to read from.
            limit: Maximum number of entries to return.
            **kwargs: Provider-specific filters (start/end time, filter pattern, …).
        """
