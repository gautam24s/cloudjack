"""GCP Pub/Sub implementation of the Queue blueprint."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exceptions
from google.cloud import pubsub_v1  # type: ignore[attr-defined]
from google.pubsub_v1.types import PubsubMessage

from cloud.base.queue import QueueBlueprint
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    QueueError,
    QueueNotFoundError,
    QueueAlreadyExistsError,
    MessageError,
)


class Queue(QueueBlueprint):
    """GCP Pub/Sub queue service.

    Pub/Sub uses a *topic + subscription* model.  ``create_queue`` creates
    both a topic and a pull subscription with the same logical name.

    Attributes:
        publisher: Pub/Sub publisher client.
        subscriber: Pub/Sub subscriber client.
        project_id: GCP project ID.
    """

    def __init__(self, config: GCPConfig) -> None:
        """Initialize Pub/Sub publisher and subscriber clients.

        Args:
            config: GCP configuration object containing project ID and credentials.
                   Expected attributes:
                   - project_id: GCP project ID
                   - credentials: Optional GCP credentials object
                   - credentials_path: Optional path to service account JSON key file
        """
        assert config.project_id is not None  # guaranteed by GCPConfig validator
        self.project_id: str = config.project_id
        self.publisher = pubsub_v1.PublisherClient(credentials=config.credentials)
        self.subscriber = pubsub_v1.SubscriberClient(credentials=config.credentials)

    def _topic_path(self, name: str) -> str:
        """Build the fully-qualified topic path."""
        return self.publisher.topic_path(self.project_id, name)  # type: ignore[no-any-return]

    def _sub_path(self, name: str) -> str:
        """Build the fully-qualified subscription path."""
        return self.subscriber.subscription_path(self.project_id, f"{name}-sub")  # type: ignore[no-any-return]

    # --- Queue lifecycle ---

    def create_queue(self, queue_name: str, **kwargs: Any) -> str:
        """Create a Pub/Sub topic + pull subscription.

        Returns:
            Subscription path.
        """
        topic_path = self._topic_path(queue_name)
        try:
            self.publisher.create_topic(request={"name": topic_path})
        except gcp_exceptions.AlreadyExists as e:
            raise QueueAlreadyExistsError(
                f"Topic '{queue_name}' already exists"
            ) from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise QueueError(f"Failed to create topic '{queue_name}'") from e

        sub_path = self._sub_path(queue_name)
        try:
            ack_deadline = kwargs.get("ack_deadline_seconds", 60)
            self.subscriber.create_subscription(
                request={
                    "name": sub_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": ack_deadline,
                }
            )
        except gcp_exceptions.GoogleAPICallError as e:
            raise QueueError(
                f"Failed to create subscription for '{queue_name}'"
            ) from e
        return sub_path

    def delete_queue(self, queue_id: str) -> None:
        """Delete a Pub/Sub subscription and its topic.

        Args:
            queue_id: Queue name (not subscription path). Both the
                      ``<name>-sub`` subscription and the ``<name>`` topic
                      are deleted.
        """
        try:
            self.subscriber.delete_subscription(
                request={"subscription": self._sub_path(queue_id)}
            )
        except gcp_exceptions.NotFound:
            pass
        except gcp_exceptions.GoogleAPICallError as e:
            raise QueueError(f"Failed to delete subscription '{queue_id}'") from e
        try:
            self.publisher.delete_topic(
                request={"topic": self._topic_path(queue_id)}
            )
        except gcp_exceptions.NotFound as e:
            raise QueueNotFoundError(f"Topic '{queue_id}' not found") from e
        except gcp_exceptions.GoogleAPICallError as e:
            raise QueueError(f"Failed to delete topic '{queue_id}'") from e

    def list_queues(self, prefix: str = "") -> list[str]:
        """List Pub/Sub topic names, optionally filtered by prefix.

        Args:
            prefix: Optional topic name prefix.

        Returns:
            A list of topic name strings (short names, not full paths).

        Raises:
            QueueError: On Pub/Sub API failure.
        """
        try:
            project_path = f"projects/{self.project_id}"
            topics = self.publisher.list_topics(request={"project": project_path})
            names = [t.name.split("/")[-1] for t in topics]
            if prefix:
                names = [n for n in names if n.startswith(prefix)]
            return names
        except gcp_exceptions.GoogleAPICallError as e:
            raise QueueError("Failed to list topics") from e

    # --- Messaging ---

    def send_message(self, queue_id: str, body: str, **kwargs: Any) -> str:
        """Publish a message to a Pub/Sub topic.

        Args:
            queue_id: Topic name (not full path).
            body: Message body.
            **kwargs: ``message_attributes`` dict for Pub/Sub message attributes.

        Returns:
            Published message ID.
        """
        try:
            topic_path = self._topic_path(queue_id)
            attrs = kwargs.get("message_attributes", {})
            future = self.publisher.publish(
                topic_path, body.encode("utf-8"), **attrs
            )
            return future.result()  # type: ignore[no-any-return]
        except Exception as e:
            raise MessageError(f"Failed to publish to '{queue_id}'") from e

    def receive_messages(
        self, queue_id: str, max_messages: int = 1, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Pull messages from a Pub/Sub subscription.

        Args:
            queue_id: Topic name (subscription ``<name>-sub`` is used).
            max_messages: Maximum messages to pull.

        Returns:
            List of dicts with ``message_id``, ``body``, ``receipt_handle``.

        Raises:
            QueueNotFoundError: If the subscription does not exist.
            MessageError: On pull failure.
        """
        try:
            sub_path = self._sub_path(queue_id)
            resp = self.subscriber.pull(
                request={
                    "subscription": sub_path,
                    "max_messages": max_messages,
                }
            )
            return [
                {
                    "message_id": msg.message.message_id,
                    "body": msg.message.data.decode("utf-8"),
                    "receipt_handle": msg.ack_id,
                }
                for msg in resp.received_messages
            ]
        except gcp_exceptions.NotFound as e:
            raise QueueNotFoundError(f"Subscription for '{queue_id}' not found") from e
        except Exception as e:
            raise MessageError(f"Failed to receive from '{queue_id}'") from e

    def delete_message(self, queue_id: str, receipt_handle: str) -> None:
        """Acknowledge a Pub/Sub message.

        Args:
            queue_id: Topic name.
            receipt_handle: Ack ID from :meth:`receive_messages`.

        Raises:
            MessageError: On acknowledgement failure.
        """
        try:
            sub_path = self._sub_path(queue_id)
            self.subscriber.acknowledge(
                request={
                    "subscription": sub_path,
                    "ack_ids": [receipt_handle],
                }
            )
        except Exception as e:
            raise MessageError(f"Failed to ack message in '{queue_id}'") from e
