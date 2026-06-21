# [C5-REAL] Exergy-Maximized
"""CORTEX Locks utilities.

Reality Level: C5-REAL
"""

import asyncio
from typing import Any


def get_loop_lock(instance: Any, attr_prefix: str) -> asyncio.Lock:
    """Get or create an asyncio.Lock tied to the current running event loop.

    Uses fallback lock if no event loop is running.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        fallback_attr = f"_fallback_{attr_prefix}_lock"
        if not hasattr(instance, fallback_attr):
            setattr(instance, fallback_attr, asyncio.Lock())
        return getattr(instance, fallback_attr)

    registry_attr = f"_{attr_prefix}_locks_by_loop"
    if not hasattr(instance, registry_attr):
        setattr(instance, registry_attr, {})
    registry = getattr(instance, registry_attr)
    if loop not in registry:
        registry[loop] = asyncio.Lock()
    return registry[loop]
