"""
Retry utilities with configurable exponential backoff.

Provides a decorator that wraps service methods with automatic retry
logic for transient failures.
"""

from __future__ import annotations

import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger("cloudjack")

# Default set of exception types considered transient / retryable.
_DEFAULT_RETRYABLE: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[BaseException], ...] | None = None,
) -> Callable:
    """Decorator: retry a function on transient exceptions with exponential backoff.

    Args:
        max_attempts: Maximum number of total attempts (including the first).
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Cap on the delay between retries.
        backoff_factor: Multiplier applied to the delay after each retry.
        retryable_exceptions: Tuple of exception types that trigger a retry.
            Defaults to ConnectionError, TimeoutError, OSError.

    Returns:
        Decorated function that retries on transient failures.
    """
    if retryable_exceptions is None:
        retryable_exceptions = _DEFAULT_RETRYABLE

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts,
                            fn.__qualname__,
                            exc,
                        )
                        raise
                    logger.warning(
                        "Attempt %d/%d for %s failed (%s), retrying in %.1fs…",
                        attempt,
                        max_attempts,
                        fn.__qualname__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
