"""Tests for core infrastructure modules."""

from unittest.mock import patch, MagicMock
import asyncio
import logging
import pytest

from cloud.base.config import AWSConfig, GCPConfig, validate_config
from cloud.base.retry import retry
from cloud.base.client_cache import ClientCache
from cloud.base.logger import CloudjackLogger, StructuredFormatter
from cloud.base.async_support import async_wrap, AsyncMixin


# ══════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════

class TestAWSConfig:
    def test_explicit_values(self):
        cfg = AWSConfig(
            aws_access_key_id="AKIA",
            aws_secret_access_key="secret",
            region_name="us-west-2",
        )
        assert cfg.aws_access_key_id == "AKIA"
        assert cfg.region_name == "us-west-2"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "env_secret")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
        cfg = AWSConfig()
        assert cfg.aws_access_key_id == "env_key"
        assert cfg.region_name == "eu-west-1"


class TestGCPConfig:
    def test_explicit_values(self):
        cfg = GCPConfig(project_id="my-proj")
        assert cfg.project_id == "my-proj"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-proj")
        cfg = GCPConfig()
        assert cfg.project_id == "env-proj"


class TestValidateConfig:
    def test_aws(self):
        cfg = validate_config("aws", {
            "aws_access_key_id": "k",
            "aws_secret_access_key": "s",
            "region_name": "us-east-1",
        })
        assert isinstance(cfg, AWSConfig)
        assert cfg.aws_access_key_id == "k"

    def test_gcp(self):
        cfg = validate_config("gcp", {"project_id": "p"})
        assert cfg.project_id == "p"

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="No config model"):
            validate_config("azure", {"key": "val"})


# ══════════════════════════════════════════════════════════════════════
# Retry
# ══════════════════════════════════════════════════════════════════════

class TestRetry:
    def test_success_no_retry(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0)
        def ok():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert ok() == "ok"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0, retryable_exceptions=(ValueError,))
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_max_attempts_exceeded(self):
        @retry(max_attempts=2, base_delay=0, retryable_exceptions=(ValueError,))
        def always_fail():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            always_fail()

    def test_non_retryable_raises_immediately(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0, retryable_exceptions=(ValueError,))
        def type_err():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            type_err()
        assert call_count == 1


# ══════════════════════════════════════════════════════════════════════
# Client Cache
# ══════════════════════════════════════════════════════════════════════

class TestClientCache:
    def test_singleton(self):
        a = ClientCache()
        b = ClientCache()
        assert a is b

    def test_caches_client(self):
        cache = ClientCache()
        cache.clear()
        factory = MagicMock(return_value="client_instance")
        c1 = cache.get_or_create("aws", "s3", {"region": "us-east-1"}, factory)
        c2 = cache.get_or_create("aws", "s3", {"region": "us-east-1"}, factory)
        assert c1 == c2
        factory.assert_called_once()

    def test_different_config_different_client(self):
        cache = ClientCache()
        cache.clear()
        factory = MagicMock(side_effect=["client_a", "client_b"])
        c1 = cache.get_or_create("aws", "s3", {"region": "us-east-1"}, factory)
        c2 = cache.get_or_create("aws", "s3", {"region": "eu-west-1"}, factory)
        assert c1 != c2
        assert factory.call_count == 2

    def test_clear(self):
        cache = ClientCache()
        cache.clear()
        factory = MagicMock(side_effect=["v1", "v2"])
        cache.get_or_create("aws", "s3", {}, factory)
        cache.clear()
        c2 = cache.get_or_create("aws", "s3", {}, factory)
        assert c2 == "v2"


# ══════════════════════════════════════════════════════════════════════
# Logger
# ══════════════════════════════════════════════════════════════════════

class TestCloudJackLogger:
    def test_log_operation(self, capfd):
        logger = CloudjackLogger("test_cj")
        logger.logger.setLevel(logging.DEBUG)
        logger.info("test message", provider="aws", service="s3", operation="create_bucket")
        captured = capfd.readouterr()
        assert "test message" in captured.err
        assert "aws" in captured.err

    def test_structured_formatter(self):
        fmt = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hi", args=(), exc_info=None,
        )
        record.provider = "gcp"
        record.request_id = "abc"
        output = fmt.format(record)
        assert '"provider": "gcp"' in output
        assert '"request_id": "abc"' in output


# ══════════════════════════════════════════════════════════════════════
# Async Support
# ══════════════════════════════════════════════════════════════════════

class TestAsyncWrap:
    def test_basic(self):
        def sync_fn(x: int) -> int:
            return x * 2

        async_fn = async_wrap(sync_fn)
        result = asyncio.run(async_fn(5))
        assert result == 10

    def test_preserves_name(self):
        def my_func():
            pass

        wrapped = async_wrap(my_func)
        assert wrapped.__name__ == "my_func"


class TestAsyncMixin:
    def test_auto_generates(self):
        class MyService(AsyncMixin):
            def do_work(self) -> str:
                return "done"

        svc = MyService()
        assert hasattr(svc, "ado_work")
        result = asyncio.run(svc.ado_work())
        assert result == "done"
