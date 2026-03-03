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
import threading
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

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


def _reserve_slot(now: float, next_allowed: list[float], interval: float) -> float:
    """Atomic slot reservation logic (Axiom 1)."""
    if now < next_allowed[0]:
        target = next_allowed[0]
        next_allowed[0] += interval
    else:
        target = now
        next_allowed[0] = now + interval
    return target


def oxygenate(min_interval: float = 0.1):
    """Decorator to ensure a function 'breathes' between calls.

    Hardened legacy: LEGION-OMEGA (400 Agents) support.
    Uses atomic timeslot reservation to handle massive concurrency without
    blocking the Event Loop significantly.
    """
    async_lock = asyncio.Lock()
    sync_lock = threading.Lock()
    next_allowed_time = [time.monotonic()]

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with async_lock:
                    target = _reserve_slot(time.monotonic(), next_allowed_time, min_interval)

                deficit = target - time.monotonic()
                if deficit > 0:
                    logger.debug("Oxygenating %s: breathing for %.3fs", func.__name__, deficit)
                    await breathe(deficit)
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[reportReturnType]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with sync_lock:
                target = _reserve_slot(time.monotonic(), next_allowed_time, min_interval)

            deficit = target - time.monotonic()
            if deficit > 0:
                time.sleep(deficit)
            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[reportReturnType]

    return decorator
