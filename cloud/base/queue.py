"""Queue / Messaging service blueprint."""

from abc import ABC, abstractmethod
from typing import Any


class QueueBlueprint(ABC):
    """Abstract interface for queue / messaging services.

    Maps to AWS SQS and GCP Pub/Sub.

    Terminology mapping:
        - **queue** → SQS Queue / Pub/Sub Topic+Subscription
        - **message** → SQS Message / Pub/Sub Message
    """

    # --- Queue lifecycle ---

    @abstractmethod
    def create_queue(self, queue_name: str, **kwargs: Any) -> str:
        """Create a new queue and return its identifier (URL / name).

        Args:
            queue_name: Logical queue name.
            **kwargs: Provider-specific creation options.

        Returns:
            Queue identifier (URL for SQS, subscription path for Pub/Sub).
        """

    @abstractmethod
    def delete_queue(self, queue_id: str) -> None:
        """Delete a queue by its identifier."""

    @abstractmethod
    def list_queues(self, prefix: str = "") -> list[str]:
        """List queue identifiers, optionally filtered by *prefix*."""

    # --- Messaging ---

    @abstractmethod
    def send_message(self, queue_id: str, body: str, **kwargs: Any) -> str:
        """Publish a message and return its message ID.

        Args:
            queue_id: Queue identifier.
            body: Message body (string).
            **kwargs: Provider-specific options (delay, attributes, …).

        Returns:
            Provider-assigned message ID.
        """

    @abstractmethod
    def receive_messages(
        self, queue_id: str, max_messages: int = 1, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Receive messages from a queue.

        Each dict in the returned list contains at least:
            - ``message_id``: Unique message identifier.
            - ``body``: Message content.
            - ``receipt_handle``: Handle for acknowledgement / deletion.

        Args:
            queue_id: Queue identifier.
            max_messages: Maximum number of messages to retrieve.
            **kwargs: Provider-specific options (wait time, visibility, …).
        """

    @abstractmethod
    def delete_message(self, queue_id: str, receipt_handle: str) -> None:
        """Acknowledge / delete a message after processing.

        Args:
            queue_id: Queue identifier.
            receipt_handle: Handle returned by :meth:`receive_messages`.
        """
