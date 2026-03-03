"""cortex.concurrency.singleflight — Request Coalescing Pattern.

Prevents redundant simultaneous I/O by collapsing multiple identical 
requests into a single execution.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger("cortex.concurrency.singleflight")


class Singleflight:
    """Collapses duplicate in-flight requests into one."""

    def __init__(self):
        self._in_flight: dict[str, asyncio.Future[Any]] = {}

    async def do(self, key: str, coro_factory: Callable[[], Awaitable[T]]) -> T:
        """Execute a call, but only if another one with the same key is not already running.
        
        If a call is in flight, wait for it and return its result.
        Otherwise, execute the call provided by the factory and share the result.
        """
        if key in self._in_flight:
            logger.debug("Singleflight: Piggybacking on in-flight request for key: %s", key)
            return await self._in_flight[key]

        # Use loop.create_future instead of asyncio.Future() for better compatibility
        future = asyncio.get_running_loop().create_future()
        self._in_flight[key] = future

        try:
            result = await coro_factory()
            future.set_result(result)
            return result
        except Exception as e:
            # Propagate error to all waiters
            future.set_exception(e)
            raise
        finally:
            # Ensure cleanup even on error
            if self._in_flight.get(key) is future:
                del self._in_flight[key]
