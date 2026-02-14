"""
Async support for Cloudjack.

Provides an ``async_wrap`` decorator that converts any synchronous method
into an awaitable coroutine using :func:`asyncio.to_thread`. This lets
every service method be called from async code without blocking the
event loop, while keeping the canonical implementations synchronous.

Usage::

    from cloud.base.async_support import async_wrap

    class MyService:
        def do_work(self) -> str:
            return "done"

        ado_work = async_wrap(do_work)

    # Then in async code:
    result = await svc.ado_work()
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


def async_wrap(
    fn: Callable[..., T],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Return an async version of *fn* that runs it in a thread.

    The wrapper preserves the original function's signature and docstring.

    Args:
        fn: A synchronous callable to wrap.

    Returns:
        An async callable with the same parameters and return type.
    """

    @functools.wraps(fn)
    async def _wrapper(*args: Any, **kwargs: Any) -> T:
        return await asyncio.to_thread(fn, *args, **kwargs)

    return _wrapper


class AsyncMixin:
    """Mixin that auto-generates ``a<method>`` async variants.

    Subclass this *alongside* a blueprint to gain async versions of every
    public method that is not already a coroutine.  The async methods are
    created once at class definition time.

    Example::

        class Storage(CloudStorageBlueprint, AsyncMixin):
            def create_bucket(self, name: str) -> None: ...
            # => self.acreate_bucket(name) is now available
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for name in list(vars(cls)):
            if name.startswith("_"):
                continue
            attr = getattr(cls, name)
            if callable(attr) and not inspect.iscoroutinefunction(attr):
                async_name = f"a{name}"
                if not hasattr(cls, async_name):
                    setattr(cls, async_name, async_wrap(attr))
