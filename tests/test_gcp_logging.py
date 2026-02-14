"""Tests for GCP Cloud Logging service."""

from unittest.mock import patch, MagicMock
import pytest

from google.api_core import exceptions as gcp_exceptions

from cloud.gcp.logging_service import Logging
from cloud.base.exceptions import (
    LoggingError,
    LogGroupNotFoundError,
    LogGroupAlreadyExistsError,
)


@pytest.fixture
def svc():
    with patch("cloud.gcp.logging_service.cloud_logging.Client") as MockClient:
        mock_client = MockClient.return_value
        instance = Logging({"project_id": "my-project"})
        yield instance, mock_client


# --- create_log_group ---

class TestCreateLogGroup:
    def test_noop_without_destination(self, svc):
        inst, client = svc
        inst.create_log_group("my-log")
        # No sink creation when no destination
        client.sink.assert_not_called()

    def test_with_destination(self, svc):
        inst, client = svc
        mock_sink = MagicMock()
        client.sink.return_value = mock_sink
        inst.create_log_group("my-log", destination="bigquery.googleapis.com/projects/p/datasets/d")
        mock_sink.create.assert_called_once()

    def test_already_exists(self, svc):
        inst, client = svc
        mock_sink = MagicMock()
        mock_sink.create.side_effect = gcp_exceptions.Conflict("exists")
        client.sink.return_value = mock_sink
        with pytest.raises(LogGroupAlreadyExistsError):
            inst.create_log_group("dup", destination="dest")


# --- delete_log_group ---

class TestDeleteLogGroup:
    def test_success(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        client.logger.return_value = mock_logger
        inst.delete_log_group("my-log")
        mock_logger.delete.assert_called_once()

    def test_not_found(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        mock_logger.delete.side_effect = gcp_exceptions.NotFound("nope")
        client.logger.return_value = mock_logger
        with pytest.raises(LogGroupNotFoundError):
            inst.delete_log_group("missing")


# --- list_log_groups ---

class TestListLogGroups:
    def test_success(self, svc):
        inst, client = svc
        mock_entry1 = MagicMock()
        mock_entry1.log_name = "projects/my-project/logs/app"
        mock_entry2 = MagicMock()
        mock_entry2.log_name = "projects/my-project/logs/web"
        client.list_entries.return_value = [mock_entry1, mock_entry2]
        result = inst.list_log_groups()
        assert "app" in result
        assert "web" in result

    def test_empty(self, svc):
        inst, client = svc
        client.list_entries.return_value = []
        assert inst.list_log_groups() == []


# --- write_log ---

class TestWriteLog:
    def test_success(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        client.logger.return_value = mock_logger
        inst.write_log("my-log", "Hello world")
        mock_logger.log_text.assert_called_once_with(
            "Hello world", severity="INFO", labels={}
        )

    def test_custom_severity(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        client.logger.return_value = mock_logger
        inst.write_log("my-log", "error msg", severity="ERROR")
        mock_logger.log_text.assert_called_once_with(
            "error msg", severity="ERROR", labels={}
        )

    def test_with_labels(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        client.logger.return_value = mock_logger
        inst.write_log("my-log", "msg", labels={"env": "prod"})
        call_kwargs = mock_logger.log_text.call_args[1]
        assert call_kwargs["labels"] == {"env": "prod"}

    def test_error(self, svc):
        inst, client = svc
        mock_logger = MagicMock()
        mock_logger.log_text.side_effect = Exception("fail")
        client.logger.return_value = mock_logger
        with pytest.raises(LoggingError):
            inst.write_log("my-log", "msg")


# --- read_logs ---

class TestReadLogs:
    def test_success(self, svc):
        inst, client = svc
        mock_entry = MagicMock()
        mock_entry.timestamp = "2024-01-01T00:00:00Z"
        mock_entry.payload = "Hello"
        mock_entry.severity = "INFO"
        client.list_entries.return_value = [mock_entry]
        logs = inst.read_logs("my-log")
        assert len(logs) == 1
        assert logs[0]["message"] == "Hello"
        assert logs[0]["severity"] == "INFO"

    def test_empty(self, svc):
        inst, client = svc
        client.list_entries.return_value = []
        assert inst.read_logs("my-log") == []

    def test_with_custom_filter(self, svc):
        inst, client = svc
        client.list_entries.return_value = []
        inst.read_logs("my-log", filter='severity="ERROR"')
        call_kwargs = client.list_entries.call_args[1]
        assert "ERROR" in call_kwargs["filter_"]

    def test_error(self, svc):
        inst, client = svc
        client.list_entries.side_effect = Exception("fail")
        with pytest.raises(LoggingError):
            inst.read_logs("my-log")
