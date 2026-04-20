"""
Client connection cache (pooling).

Avoids creating redundant cloud SDK clients when the same provider + config
combination is requested multiple times via the universal factory.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ClientCache:
    """Thread-safe, in-process cache for service instances keyed by provider + config hash."""

    _instance: ClientCache | None = None
    # Class-level lock guards the singleton creation itself. A separate
    # per-instance lock (``self._lock``) guards the cache dict.
    _singleton_lock: threading.Lock = threading.Lock()
    _cache: dict[str, Any]
    _lock: threading.Lock

    def __new__(cls) -> ClientCache:
        # Double-checked locking: the fast path avoids lock contention once
        # the singleton is initialised, and the slow path recheques inside
        # the lock to prevent two threads from racing the first-time init.
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._cache = {}
                    inst._lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    @staticmethod
    def _make_key(cloud_provider: str, service_name: str, config: dict) -> str:
        """Produce a deterministic cache key from provider, service, and config."""
        # Sort keys so dict ordering doesn't affect the hash.
        serialised = json.dumps(
            {"provider": cloud_provider, "service": service_name, "config": config},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(serialised.encode()).hexdigest()

    def get_or_create(
        self,
        cloud_provider: str,
        service_name: str,
        config: dict,
        factory: Callable[[dict], T],
    ) -> T:
        """Return a cached service instance or create one via *factory*.

        The return type is inferred from *factory*, so callers keep full
        editor autocomplete on the returned service.

        Args:
            cloud_provider: Cloud provider name (e.g. 'aws').
            service_name: Service name (e.g. 'storage').
            factory: Callable(config) that creates a new service instance.
            config: Configuration dict.

        Returns:
            The cached (or newly-created) service instance.
        """
        key = self._make_key(cloud_provider, service_name, config)
        with self._lock:
            if key not in self._cache:
                self._cache[key] = factory(config)
            cached: T = self._cache[key]
            return cached

    def clear(self) -> None:
        """Flush all cached service instances."""
        with self._lock:
            self._cache.clear()
