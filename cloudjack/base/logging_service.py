"""Cloud logging service interface."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from cloudjack.base.types import LogEntryDict


class LoggingService(ABC):
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
    ) -> list[LogEntryDict]:
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

    # --- Async variants ---

    async def acreate_log_group(self, name: str, **kwargs: Any) -> None:
        """Async variant of :meth:`create_log_group` (runs in a worker thread)."""
        return await asyncio.to_thread(self.create_log_group, name, **kwargs)

    async def adelete_log_group(self, name: str) -> None:
        """Async variant of :meth:`delete_log_group` (runs in a worker thread)."""
        return await asyncio.to_thread(self.delete_log_group, name)

    async def alist_log_groups(self, prefix: str = "") -> list[str]:
        """Async variant of :meth:`list_log_groups` (runs in a worker thread)."""
        return await asyncio.to_thread(self.list_log_groups, prefix)

    async def awrite_log(
        self,
        log_group: str,
        message: str,
        *,
        severity: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Async variant of :meth:`write_log` (runs in a worker thread)."""
        return await asyncio.to_thread(
            self.write_log, log_group, message, severity=severity, **kwargs
        )

    async def aread_logs(
        self,
        log_group: str,
        *,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[LogEntryDict]:
        """Async variant of :meth:`read_logs` (runs in a worker thread)."""
        return await asyncio.to_thread(
            self.read_logs, log_group, limit=limit, **kwargs
        )
