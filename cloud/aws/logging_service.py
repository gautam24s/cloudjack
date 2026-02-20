"""AWS CloudWatch Logs implementation of the Logging blueprint."""

from __future__ import annotations

import time
from typing import Any, NoReturn

import boto3
from botocore.exceptions import ClientError

from cloud.base.logging_service import LoggingBlueprint
from cloud.base.exceptions import (
    LoggingError,
    LogGroupNotFoundError,
    LogGroupAlreadyExistsError,
)
from cloud.base.config import AWSConfig

_ERROR_MAP: dict[str, type[LoggingError]] = {
    "ResourceNotFoundException": LogGroupNotFoundError,
    "ResourceAlreadyExistsException": LogGroupAlreadyExistsError,
}


def _handle(e: ClientError, msg: str) -> NoReturn:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or LoggingError)(msg) from e


_DEFAULT_STREAM = "default"


class Logging(LoggingBlueprint):
    """AWS CloudWatch Logs service.

    Attributes:
        client: boto3 CloudWatch Logs client.
    """

    def __init__(self, config: AWSConfig) -> None:
        """Initialize the CloudWatch Logs client.

        Args:
            config: AWS configuration object containing credentials and region.
                   Expected attributes:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "logs",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )

    # --- Log group lifecycle ---

    def create_log_group(self, name: str, **kwargs: Any) -> None:
        """Create a CloudWatch Logs log group.

        Args:
            name: Log group name.
            **kwargs: ``retention_days`` — sets a retention policy.

        Raises:
            LogGroupAlreadyExistsError: If the log group already exists.
            LoggingError: On CloudWatch API failure.
        """
        try:
            params: dict[str, Any] = {"logGroupName": name}
            if "retention_days" in kwargs:
                self.client.create_log_group(**params)
                self.client.put_retention_policy(
                    logGroupName=name,
                    retentionInDays=kwargs["retention_days"],
                )
                return
            self.client.create_log_group(**params)
        except ClientError as e:
            _handle(e, f"Failed to create log group '{name}'")

    def delete_log_group(self, name: str) -> None:
        """Delete a CloudWatch Logs log group.

        Args:
            name: Log group name.

        Raises:
            LogGroupNotFoundError: If the log group does not exist.
        """
        try:
            self.client.delete_log_group(logGroupName=name)
        except ClientError as e:
            _handle(e, f"Failed to delete log group '{name}'")

    def list_log_groups(self, prefix: str = "") -> list[str]:
        """List CloudWatch log group names.

        Args:
            prefix: Optional name prefix filter.

        Returns:
            A list of log group name strings.

        Raises:
            LoggingError: On CloudWatch API failure.
        """
        try:
            params: dict[str, Any] = {}
            if prefix:
                params["logGroupNamePrefix"] = prefix
            groups: list[str] = []
            paginator = self.client.get_paginator("describe_log_groups")
            for page in paginator.paginate(**params):
                groups.extend(g["logGroupName"] for g in page.get("logGroups", []))
            return groups
        except ClientError as e:
            _handle(e, "Failed to list log groups")

    # --- Log operations ---

    def _ensure_stream(self, log_group: str, stream_name: str) -> None:
        """Create the log stream if it doesn't exist."""
        try:
            self.client.create_log_stream(
                logGroupName=log_group, logStreamName=stream_name
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                _handle(e, f"Failed to create log stream '{stream_name}'")

    def write_log(
        self,
        log_group: str,
        message: str,
        *,
        severity: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Write a log event to CloudWatch Logs.

        Args:
            log_group: Target log group name.
            message: Log message string.
            severity: Log level label prepended to the message.
            **kwargs: ``stream_name`` — target log stream
                (default ``"default"``).

        Raises:
            LogGroupNotFoundError: If the log group does not exist.
            LoggingError: On CloudWatch API failure.
        """
        stream = kwargs.get("stream_name", _DEFAULT_STREAM)
        self._ensure_stream(log_group, stream)
        try:
            self.client.put_log_events(
                logGroupName=log_group,
                logStreamName=stream,
                logEvents=[
                    {
                        "timestamp": int(time.time() * 1000),
                        "message": f"[{severity}] {message}",
                    }
                ],
            )
        except ClientError as e:
            _handle(e, f"Failed to write log to '{log_group}'")

    def read_logs(
        self,
        log_group: str,
        *,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Read log events from a CloudWatch log group.

        Args:
            log_group: Log group to read from.
            limit: Maximum number of events to return.
            **kwargs: ``start_time``, ``end_time`` (epoch ms),
                ``filter_pattern``.

        Returns:
            List of dicts with ``timestamp``, ``message``,
            ``severity``, ``stream``.

        Raises:
            LogGroupNotFoundError: If the log group does not exist.
        """
        try:
            params: dict[str, Any] = {
                "logGroupName": log_group,
                "limit": limit,
                "interleaved": True,
            }
            if "start_time" in kwargs:
                params["startTime"] = kwargs["start_time"]
            if "end_time" in kwargs:
                params["endTime"] = kwargs["end_time"]
            if "filter_pattern" in kwargs:
                params["filterPattern"] = kwargs["filter_pattern"]
            resp = self.client.filter_log_events(**params)
            results: list[dict[str, Any]] = []
            for e in resp.get("events", []):
                raw_msg = e.get("message", "")
                # Parse severity from "[SEVERITY] message" format written by write_log
                severity = "INFO"
                message = raw_msg
                if raw_msg.startswith("["):
                    bracket_end = raw_msg.find("]")
                    if bracket_end > 1:
                        severity = raw_msg[1:bracket_end]
                        message = raw_msg[bracket_end + 1:].lstrip()
                results.append({
                    "timestamp": e.get("timestamp", 0),
                    "message": message,
                    "severity": severity,
                    "stream": e.get("logStreamName", ""),
                })
            return results
        except ClientError as e:
            _handle(e, f"Failed to read logs from '{log_group}'")
