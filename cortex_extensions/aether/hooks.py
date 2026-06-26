# [C5-REAL] Exergy-Maximized
"""Aether Hooks - Deterministic Execution Sandboxing.

Provides decorators and wrappers to enforce limits on agent tool invocation.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger("cortex_extensions.aether.hooks")


def hooked_tool_execution(
    timeout_limit: float = 5.0,
) -> Callable[[Callable[..., Any]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator to enforce deterministic timeout_limit (in seconds) on tool execution.

    If the decorated function is synchronous, it runs it in a separate thread using
    asyncio.to_thread, wrapping it with asyncio.wait_for.
    If the decorated function is asynchronous, it wraps it with asyncio.wait_for directly.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if inspect.iscoroutinefunction(func):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_limit)
                except asyncio.TimeoutError:
                    logger.error("Tool execution timed out after %s seconds (async)", timeout_limit)
                    return f"[ERROR] Tool execution timed out after {timeout_limit} seconds"
            else:
                # Wrap synchronous execution in asyncio.to_thread
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(func, *args, **kwargs), timeout=timeout_limit
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "Tool execution timed out after %s seconds (sync via thread)", timeout_limit
                    )
                    return f"[ERROR] Tool execution timed out after {timeout_limit} seconds"

        return async_wrapper

    return decorator
