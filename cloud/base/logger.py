"""
Structured logging for Cloudjack.

Provides a pre-configured logger that emits JSON-structured log records
with request context (provider, service, operation) for easy filtering
in log aggregation tools.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any extras injected via CloudjackLogger.log_operation
        for key in ("request_id", "provider", "service", "operation"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry)


class CloudjackLogger:
    """Convenience wrapper around :mod:`logging` for Cloudjack operations."""

    def __init__(self, name: str = "cloudjack") -> None:
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_operation(
        self,
        level: int,
        message: str,
        *,
        provider: str | None = None,
        service: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        exc_info: bool = False,
    ) -> None:
        """Emit a structured log record with cloud operation context.

        Args:
            level: Logging level (e.g. logging.INFO).
            message: Human-readable message.
            provider: Cloud provider name.
            service: Service name (e.g. 'storage').
            operation: Operation name (e.g. 'create_bucket').
            request_id: Optional correlation ID; auto-generated if omitted.
            exc_info: Whether to include exception info.
        """
        extra = {
            "provider": provider,
            "service": service,
            "operation": operation,
            "request_id": request_id or uuid.uuid4().hex[:12],
        }
        self.logger.log(level, message, extra=extra, exc_info=exc_info)

    def info(self, message: str, **kwargs: Any) -> None:
        self.log_operation(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.log_operation(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.log_operation(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.log_operation(logging.DEBUG, message, **kwargs)


# Module-level singleton
cj_logger = CloudjackLogger()
