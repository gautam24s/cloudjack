"""Tests for GCP Pub/Sub Queue service."""

from unittest.mock import patch, MagicMock
import pytest

from google.api_core import exceptions as gcp_exceptions

from cloud.gcp.queue import Queue
from cloud.base.config import GCPConfig
from cloud.base.exceptions import (
    QueueError,
    QueueNotFoundError,
    QueueAlreadyExistsError,
    MessageError,
)


@pytest.fixture
def svc():
    with (
        patch("cloud.gcp.queue.pubsub_v1.PublisherClient") as MockPub,
        patch("cloud.gcp.queue.pubsub_v1.SubscriberClient") as MockSub,
    ):
        mock_pub = MockPub.return_value
        mock_sub = MockSub.return_value
        mock_pub.topic_path.side_effect = lambda p, t: f"projects/{p}/topics/{t}"
        mock_sub.subscription_path.side_effect = lambda p, s: f"projects/{p}/subscriptions/{s}"
        instance = Queue(GCPConfig(project_id="my-project"))
        yield instance, mock_pub, mock_sub


# --- create_queue ---

class TestCreateQueue:
    def test_success(self, svc):
        inst, pub, sub = svc
        result = inst.create_queue("my-queue")
        pub.create_topic.assert_called_once()
        sub.create_subscription.assert_called_once()
        assert "my-queue-sub" in result

    def test_already_exists(self, svc):
        inst, pub, sub = svc
        pub.create_topic.side_effect = gcp_exceptions.AlreadyExists("exists")
        with pytest.raises(QueueAlreadyExistsError):
            inst.create_queue("dup")

    def test_generic_error(self, svc):
        inst, pub, sub = svc
        pub.create_topic.side_effect = gcp_exceptions.InternalServerError("fail")
        with pytest.raises(QueueError):
            inst.create_queue("fail")


# --- delete_queue ---

class TestDeleteQueue:
    def test_success(self, svc):
        inst, pub, sub = svc
        inst.delete_queue("my-queue")
        sub.delete_subscription.assert_called_once()
        pub.delete_topic.assert_called_once()

    def test_topic_not_found(self, svc):
        inst, pub, sub = svc
        pub.delete_topic.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(QueueNotFoundError):
            inst.delete_queue("missing")

    def test_sub_not_found_continues(self, svc):
        inst, pub, sub = svc
        sub.delete_subscription.side_effect = gcp_exceptions.NotFound("nope")
        inst.delete_queue("q")  # should not raise
        pub.delete_topic.assert_called_once()


# --- list_queues ---

class TestListQueues:
    def test_success(self, svc):
        inst, pub, sub = svc
        mock_topic1 = MagicMock()
        mock_topic1.name = "projects/my-project/topics/q1"
        mock_topic2 = MagicMock()
        mock_topic2.name = "projects/my-project/topics/q2"
        pub.list_topics.return_value = [mock_topic1, mock_topic2]
        result = inst.list_queues()
        assert result == ["q1", "q2"]

    def test_with_prefix(self, svc):
        inst, pub, sub = svc
        mock_topic = MagicMock()
        mock_topic.name = "projects/my-project/topics/test-q"
        pub.list_topics.return_value = [mock_topic]
        result = inst.list_queues(prefix="test")
        assert result == ["test-q"]


# --- send_message ---

class TestSendMessage:
    def test_success(self, svc):
        inst, pub, sub = svc
        future = MagicMock()
        future.result.return_value = "msg-id-123"
        pub.publish.return_value = future
        mid = inst.send_message("my-queue", "hello")
        assert mid == "msg-id-123"

    def test_error(self, svc):
        inst, pub, sub = svc
        pub.publish.side_effect = Exception("publish failed")
        with pytest.raises(MessageError):
            inst.send_message("q", "body")


# --- receive_messages ---

class TestReceiveMessages:
    def test_success(self, svc):
        inst, pub, sub = svc
        mock_msg = MagicMock()
        mock_msg.message.message_id = "m1"
        mock_msg.message.data = b"body"
        mock_msg.ack_id = "ack1"
        mock_resp = MagicMock()
        mock_resp.received_messages = [mock_msg]
        sub.pull.return_value = mock_resp
        msgs = inst.receive_messages("q")
        assert len(msgs) == 1
        assert msgs[0]["message_id"] == "m1"
        assert msgs[0]["body"] == "body"

    def test_not_found(self, svc):
        inst, pub, sub = svc
        sub.pull.side_effect = gcp_exceptions.NotFound("nope")
        with pytest.raises(QueueNotFoundError):
            inst.receive_messages("missing")


# --- delete_message ---

class TestDeleteMessage:
    def test_success(self, svc):
        inst, pub, sub = svc
        inst.delete_message("q", "ack1")
        sub.acknowledge.assert_called_once()

    def test_error(self, svc):
        inst, pub, sub = svc
        sub.acknowledge.side_effect = Exception("ack failed")
        with pytest.raises(MessageError):
            inst.delete_message("q", "bad-ack")
