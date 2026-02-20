"""AWS SQS implementation of the Queue blueprint."""

from __future__ import annotations

from typing import Any, NoReturn

import boto3
from botocore.exceptions import ClientError

from cloud.base.queue import QueueBlueprint
from cloud.base.exceptions import (
    QueueError,
    QueueNotFoundError,
    QueueAlreadyExistsError,
    MessageError,
)
from cloud.base.config import AWSConfig

_ERROR_MAP: dict[str, type[QueueError]] = {
    "AWS.SimpleQueueService.NonExistentQueue": QueueNotFoundError,
    "QueueDoesNotExist": QueueNotFoundError,
    "QueueDeletedRecently": QueueNotFoundError,
    "QueueAlreadyExists": QueueAlreadyExistsError,
}


def _handle(e: ClientError, msg: str) -> NoReturn:
    exc = _ERROR_MAP.get(e.response["Error"]["Code"])
    raise (exc or QueueError)(msg) from e


class Queue(QueueBlueprint):
    """AWS SQS queue service.

    Attributes:
        client: boto3 SQS client.
    """

    def __init__(self, config: AWSConfig) -> None:
        """Initialize the SQS client.

        Args:
            config: AWS configuration object containing credentials and region.
                   Expected attributes:
                   - aws_access_key_id: AWS access key ID
                   - aws_secret_access_key: AWS secret access key
                   - region_name: AWS region name (e.g., 'us-east-1')
        """
        self.client = boto3.client(
            "sqs",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
        )

    # --- Queue lifecycle ---

    def create_queue(self, queue_name: str, **kwargs: Any) -> str:
        """Create an SQS queue.

        Returns:
            Queue URL.
        """
        try:
            attrs: dict[str, str] = {}
            if "delay_seconds" in kwargs:
                attrs["DelaySeconds"] = str(kwargs["delay_seconds"])
            if "visibility_timeout" in kwargs:
                attrs["VisibilityTimeout"] = str(kwargs["visibility_timeout"])
            resp = self.client.create_queue(
                QueueName=queue_name,
                Attributes=attrs or {},
            )
            return resp["QueueUrl"]  # type: ignore[no-any-return]
        except ClientError as e:
            _handle(e, f"Failed to create queue '{queue_name}'")

    def delete_queue(self, queue_id: str) -> None:
        """Delete an SQS queue.

        Args:
            queue_id: Queue URL returned by :meth:`create_queue`.

        Raises:
            QueueNotFoundError: If the queue does not exist.
            QueueError: On any other SQS error.
        """
        try:
            self.client.delete_queue(QueueUrl=queue_id)
        except ClientError as e:
            _handle(e, f"Failed to delete queue '{queue_id}'")

    def list_queues(self, prefix: str = "") -> list[str]:
        """List SQS queue URLs, optionally filtered by name prefix.

        Args:
            prefix: Optional queue name prefix.

        Returns:
            A list of queue URL strings.

        Raises:
            QueueError: On SQS API failure.
        """
        try:
            params: dict[str, Any] = {}
            if prefix:
                params["QueueNamePrefix"] = prefix
            resp = self.client.list_queues(**params)
            return resp.get("QueueUrls", [])  # type: ignore[no-any-return]
        except ClientError as e:
            _handle(e, "Failed to list queues")

    # --- Messaging ---

    def send_message(self, queue_id: str, body: str, **kwargs: Any) -> str:
        """Send a message to an SQS queue.

        Args:
            queue_id: Queue URL.
            body: Message body string.
            **kwargs: ``delay_seconds``, ``message_attributes``.

        Returns:
            SQS-assigned message ID.

        Raises:
            MessageError: If the send fails.
        """
        try:
            params: dict[str, Any] = {"QueueUrl": queue_id, "MessageBody": body}
            if "delay_seconds" in kwargs:
                params["DelaySeconds"] = kwargs["delay_seconds"]
            if "message_attributes" in kwargs:
                params["MessageAttributes"] = kwargs["message_attributes"]
            resp = self.client.send_message(**params)
            return resp["MessageId"]  # type: ignore[no-any-return]
        except ClientError as e:
            raise MessageError(f"Failed to send message to '{queue_id}'") from e

    def receive_messages(
        self, queue_id: str, max_messages: int = 1, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Receive messages from an SQS queue.

        Args:
            queue_id: Queue URL.
            max_messages: Max messages to receive (capped at 10 by SQS).
            **kwargs: ``wait_time_seconds``, ``visibility_timeout``.

        Returns:
            List of dicts with ``message_id``, ``body``, ``receipt_handle``.

        Raises:
            MessageError: If the receive fails.
        """
        try:
            params: dict[str, Any] = {
                "QueueUrl": queue_id,
                "MaxNumberOfMessages": min(max_messages, 10),
            }
            if "wait_time_seconds" in kwargs:
                params["WaitTimeSeconds"] = kwargs["wait_time_seconds"]
            if "visibility_timeout" in kwargs:
                params["VisibilityTimeout"] = kwargs["visibility_timeout"]
            resp = self.client.receive_message(**params)
            return [
                {
                    "message_id": m["MessageId"],
                    "body": m["Body"],
                    "receipt_handle": m["ReceiptHandle"],
                }
                for m in resp.get("Messages", [])
            ]
        except ClientError as e:
            raise MessageError(f"Failed to receive messages from '{queue_id}'") from e

    def delete_message(self, queue_id: str, receipt_handle: str) -> None:
        """Delete (acknowledge) a message from an SQS queue.

        Args:
            queue_id: Queue URL.
            receipt_handle: Handle from :meth:`receive_messages`.

        Raises:
            MessageError: If the delete fails.
        """
        try:
            self.client.delete_message(
                QueueUrl=queue_id, ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            raise MessageError(f"Failed to delete message from '{queue_id}'") from e
