# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Architectural Respiration (PULMONES).

Axiom 2: Entropic Asymmetry.
A system without space suffocates. These primitives ensure that tight loops,
heavy operations, and system monitoring tasks yield control to the async
event loop, oxygenating the architecture and preventing UI/daemon freezes.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

logger = logging.getLogger("cortex.respiration")

P = ParamSpec("P")
R = TypeVar("R")

__all__ = ["breathe", "oxygenate"]


async def breathe(interval: float = 0.0) -> None:
    """Yield control back to the event loop.

    In a monolithic synchronous loop, a `time.sleep` halts the entire process.
    Here, `breathe` provides oxygen by allowing other coroutines to execute.
    If interval is 0, it simply forces a context switch.
    """
    await asyncio.sleep(interval)


def oxygenate(min_interval: float = 0.1) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator: Ensures a minimum time passes between executions.

    Rate-limits heavy functions (like file parsing or fact aggregation)
    so they don't consume the entire CPU. If called too frequently,
    it introduces a small blocking delay (if sync) or yields (if async).
    
    [LEGION-Ω Hardened]: Uses atomic timeslot reservation. If 400 agents hit
    this concurrently, they don't block each other. They each instantly reserve 
    a slot in the future and sleep concurrently until their exact turn.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            lock = asyncio.Lock()
            next_allowed_time = 0.0

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                nonlocal next_allowed_time
                
                async with lock:
                    now = time.monotonic()
                    if now < next_allowed_time:
                        deficit = next_allowed_time - now
                        next_allowed_time += min_interval
                    else:
                        deficit = 0.0
                        next_allowed_time = now + min_interval

                if deficit > 0:
                    logger.debug("Oxygenating %s: breathing for %.3fs", func.__name__, deficit)
                    await breathe(deficit)

                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[reportReturnType]

        else:
            import threading
            lock = threading.Lock()
            next_allowed_time = 0.0

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                nonlocal next_allowed_time
                
                with lock:
                    now = time.monotonic()
                    if now < next_allowed_time:
                        deficit = next_allowed_time - now
                        next_allowed_time += min_interval
                    else:
                        deficit = 0.0
                        next_allowed_time = now + min_interval

                if deficit > 0:
                    # For sync functions we have no choice but to block,
                    # but we do it outside the lock to prevent total starvation.
                    time.sleep(deficit)

                return func(*args, **kwargs)

            return sync_wrapper

    return decorator
