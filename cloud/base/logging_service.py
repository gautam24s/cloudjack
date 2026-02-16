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

        Keyword Args:
            retention_days (int): Log retention period in days *(AWS)*.
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

        Keyword Args:
            stream_name (str): Target log stream, default
                ``"default"`` *(AWS)*.
            labels (dict): Dict of key-value labels to attach *(GCP)*.
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

        Keyword Args:
            filter_pattern (str): Filter/search string for log
                entries *(AWS, GCP)*.
            start_time (int): Start time in epoch milliseconds *(AWS)*.
            end_time (int): End time in epoch milliseconds *(AWS)*.
        """
