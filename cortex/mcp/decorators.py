"""
MCP tool decorators to hide boilerplate code like acquiring database connections.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.mcp.server import _MCPContext

__all__ = ["with_db"]


def with_db(
    ctx: _MCPContext,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator to inject a database connection to an MCP tool.

    This abstracts away `await ctx.ensure_ready()` and `async with ctx.pool.acquire() as conn:`.
    It removes the `conn` parameter from the visible signature so that FastMCP does not parse
    it as an expected tool argument.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        sig = inspect.signature(func)
        params = [p for name, p in sig.parameters.items() if name != "conn"]
        new_sig = sig.replace(parameters=params)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await ctx.ensure_ready()
            async with ctx.pool.acquire() as conn:
                return await func(*args, conn=conn, **kwargs)

        wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
        return wrapper

    return decorator
