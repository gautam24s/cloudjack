"""Tests for AWS CloudWatch Logs service."""

from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

from cloud.aws.logging_service import Logging
from cloud.base.exceptions import (
    LoggingError,
    LogGroupNotFoundError,
    LogGroupAlreadyExistsError,
)


def _client_error(code: str, msg: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, "op")


@pytest.fixture
def svc():
    with patch("cloud.aws.logging_service.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        instance = Logging({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region_name": "us-east-1",
        })
        yield instance, mock_client


# --- create_log_group ---

class TestCreateLogGroup:
    def test_success(self, svc):
        inst, client = svc
        inst.create_log_group("/app/logs")
        client.create_log_group.assert_called_once_with(logGroupName="/app/logs")

    def test_with_retention(self, svc):
        inst, client = svc
        inst.create_log_group("/app/logs", retention_days=30)
        client.create_log_group.assert_called_once()
        client.put_retention_policy.assert_called_once_with(
            logGroupName="/app/logs", retentionInDays=30
        )

    def test_already_exists(self, svc):
        inst, client = svc
        client.create_log_group.side_effect = _client_error("ResourceAlreadyExistsException")
        with pytest.raises(LogGroupAlreadyExistsError):
            inst.create_log_group("dup")

    def test_generic_error(self, svc):
        inst, client = svc
        client.create_log_group.side_effect = _client_error("ServiceUnavailableException")
        with pytest.raises(LoggingError):
            inst.create_log_group("fail")


# --- delete_log_group ---

class TestDeleteLogGroup:
    def test_success(self, svc):
        inst, client = svc
        inst.delete_log_group("/app/logs")
        client.delete_log_group.assert_called_once_with(logGroupName="/app/logs")

    def test_not_found(self, svc):
        inst, client = svc
        client.delete_log_group.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(LogGroupNotFoundError):
            inst.delete_log_group("missing")


# --- list_log_groups ---

class TestListLogGroups:
    def test_success(self, svc):
        inst, client = svc
        client.describe_log_groups.return_value = {
            "logGroups": [
                {"logGroupName": "/app/web"},
                {"logGroupName": "/app/api"},
            ]
        }
        groups = inst.list_log_groups()
        assert groups == ["/app/web", "/app/api"]

    def test_with_prefix(self, svc):
        inst, client = svc
        client.describe_log_groups.return_value = {"logGroups": [{"logGroupName": "/app/web"}]}
        inst.list_log_groups(prefix="/app")
        client.describe_log_groups.assert_called_once_with(logGroupNamePrefix="/app")

    def test_empty(self, svc):
        inst, client = svc
        client.describe_log_groups.return_value = {"logGroups": []}
        assert inst.list_log_groups() == []


# --- write_log ---

class TestWriteLog:
    def test_success(self, svc):
        inst, client = svc
        # _ensure_stream should be called first
        inst.write_log("/app/logs", "Hello world")
        client.create_log_stream.assert_called_once()
        client.put_log_events.assert_called_once()
        call_kwargs = client.put_log_events.call_args[1]
        assert call_kwargs["logGroupName"] == "/app/logs"
        assert "[INFO]" in call_kwargs["logEvents"][0]["message"]

    def test_custom_stream(self, svc):
        inst, client = svc
        inst.write_log("/app/logs", "test", stream_name="custom")
        client.create_log_stream.assert_called_once_with(
            logGroupName="/app/logs", logStreamName="custom"
        )

    def test_custom_severity(self, svc):
        inst, client = svc
        inst.write_log("/app/logs", "bad", severity="ERROR")
        call_kwargs = client.put_log_events.call_args[1]
        assert "[ERROR]" in call_kwargs["logEvents"][0]["message"]

    def test_error(self, svc):
        inst, client = svc
        client.put_log_events.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(LogGroupNotFoundError):
            inst.write_log("missing", "msg")


# --- read_logs ---

class TestReadLogs:
    def test_success(self, svc):
        inst, client = svc
        client.filter_log_events.return_value = {
            "events": [
                {"timestamp": 1000, "message": "[INFO] Hi", "logStreamName": "s"},
            ]
        }
        logs = inst.read_logs("/app/logs")
        assert len(logs) == 1
        assert logs[0]["message"] == "[INFO] Hi"

    def test_with_filter(self, svc):
        inst, client = svc
        client.filter_log_events.return_value = {"events": []}
        inst.read_logs("/app/logs", filter_pattern="ERROR")
        call_kwargs = client.filter_log_events.call_args[1]
        assert call_kwargs["filterPattern"] == "ERROR"

    def test_empty(self, svc):
        inst, client = svc
        client.filter_log_events.return_value = {"events": []}
        assert inst.read_logs("/app/logs") == []

    def test_error(self, svc):
        inst, client = svc
        client.filter_log_events.side_effect = _client_error("ResourceNotFoundException")
        with pytest.raises(LogGroupNotFoundError):
            inst.read_logs("missing")
