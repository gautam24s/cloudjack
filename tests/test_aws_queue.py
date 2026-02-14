"""Tests for AWS SQS Queue service."""

from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.queue import Queue
from cloud.base.exceptions import (
    QueueError,
    QueueNotFoundError,
    QueueAlreadyExistsError,
    MessageError,
)


def _client_error(code: str, msg: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, "op")


@pytest.fixture
def svc():
    with patch("cloud.aws.queue.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = Queue({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1",
        })
        yield instance, mock_client


# --- create_queue ---

class TestCreateQueue:
    def test_success(self, svc):
        inst, client = svc
        client.create_queue.return_value = {"QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/my-queue"}
        url = inst.create_queue("my-queue")
        assert "my-queue" in url
        client.create_queue.assert_called_once()

    def test_with_attributes(self, svc):
        inst, client = svc
        client.create_queue.return_value = {"QueueUrl": "url"}
        inst.create_queue("q", delay_seconds=5, visibility_timeout=30)
        call_kwargs = client.create_queue.call_args
        assert call_kwargs[1]["Attributes"]["DelaySeconds"] == "5"
        assert call_kwargs[1]["Attributes"]["VisibilityTimeout"] == "30"

    def test_already_exists(self, svc):
        inst, client = svc
        client.create_queue.side_effect = _client_error("QueueAlreadyExists")
        with pytest.raises(QueueAlreadyExistsError):
            inst.create_queue("existing")

    def test_generic_error(self, svc):
        inst, client = svc
        client.create_queue.side_effect = _client_error("UnknownError")
        with pytest.raises(QueueError):
            inst.create_queue("fail")


# --- delete_queue ---

class TestDeleteQueue:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_queue("https://sqs/q")
        client.delete_queue.assert_called_once_with(QueueUrl="https://sqs/q")

    def test_not_found(self, svc):
        inst, client = svc
        client.delete_queue.side_effect = _client_error("AWS.SimpleQueueService.NonExistentQueue")
        with pytest.raises(QueueNotFoundError):
            inst.delete_queue("missing")


# --- list_queues ---

class TestListQueues:
    def test_success(self, svc):
        inst, client = svc
        client.list_queues.return_value = {"QueueUrls": ["url1", "url2"]}
        assert inst.list_queues() == ["url1", "url2"]

    def test_empty(self, svc):
        inst, client = svc
        client.list_queues.return_value = {}
        assert inst.list_queues() == []

    def test_with_prefix(self, svc):
        inst, client = svc
        client.list_queues.return_value = {"QueueUrls": ["url1"]}
        inst.list_queues(prefix="test")
        client.list_queues.assert_called_once_with(QueueNamePrefix="test")


# --- send_message ---

class TestSendMessage:
    def test_success(self, svc):
        inst, client = svc
        client.send_message.return_value = {"MessageId": "msg-123"}
        mid = inst.send_message("url", "hello")
        assert mid == "msg-123"

    def test_with_delay(self, svc):
        inst, client = svc
        client.send_message.return_value = {"MessageId": "id"}
        inst.send_message("url", "body", delay_seconds=10)
        call_kwargs = client.send_message.call_args[1]
        assert call_kwargs["DelaySeconds"] == 10

    def test_error(self, svc):
        inst, client = svc
        client.send_message.side_effect = _client_error("ServiceUnavailable")
        with pytest.raises(MessageError):
            inst.send_message("url", "body")


# --- receive_messages ---

class TestReceiveMessages:
    def test_success(self, svc):
        inst, client = svc
        client.receive_message.return_value = {
            "Messages": [
                {"MessageId": "m1", "Body": "b1", "ReceiptHandle": "rh1"},
            ]
        }
        msgs = inst.receive_messages("url")
        assert len(msgs) == 1
        assert msgs[0]["message_id"] == "m1"
        assert msgs[0]["body"] == "b1"
        assert msgs[0]["receipt_handle"] == "rh1"

    def test_empty(self, svc):
        inst, client = svc
        client.receive_message.return_value = {}
        assert inst.receive_messages("url") == []

    def test_max_messages_capped(self, svc):
        inst, client = svc
        client.receive_message.return_value = {"Messages": []}
        inst.receive_messages("url", max_messages=20)
        call_kwargs = client.receive_message.call_args[1]
        assert call_kwargs["MaxNumberOfMessages"] == 10  # SQS max


# --- delete_message ---

class TestDeleteMessage:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_message("url", "rh1")
        client.delete_message.assert_called_once_with(QueueUrl="url", ReceiptHandle="rh1")

    def test_error(self, svc):
        inst, client = svc
        client.delete_message.side_effect = _client_error("ReceiptHandleIsInvalid")
        with pytest.raises(MessageError):
            inst.delete_message("url", "bad")
