"""
Client connection cache (pooling).

Avoids creating redundant cloud SDK clients when the same provider + config
combination is requested multiple times via the universal factory.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any


class ClientCache:
    """Thread-safe, in-process cache for service instances keyed by provider + config hash."""

    _instance: ClientCache | None = None
    _cache: dict[str, Any]
    _lock: threading.Lock

    def __new__(cls) -> ClientCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
            cls._instance._lock = threading.Lock()
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
        factory: Any,
    ) -> Any:
        """Return a cached service instance or create one via *factory*.

        Args:
            cloud_provider: Cloud provider name (e.g. 'aws').
            service_name: Service name (e.g. 'storage').
            config: Configuration dict.
            factory: Callable(config) that creates a new service instance.

        Returns:
            The cached (or newly-created) service instance.
        """
        key = self._make_key(cloud_provider, service_name, config)
        with self._lock:
            if key not in self._cache:
                self._cache[key] = factory(config)
            return self._cache[key]

    def clear(self) -> None:
        """Flush all cached service instances."""
        with self._lock:
            self._cache.clear()
