# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Sovereign Event Loop (KETER-∞ Ola 2).

Centralizes asyncio event loop policy with automatic uvloop
acceleration on supported platforms (Linux/macOS).

Architecture:
    ┌──────────────────────┐
    │   cortex.event_loop  │
    │   sovereign_run()    │
    ├──────────────────────┤
    │  uvloop (if avail.)  │ ← kqueue (macOS) / epoll (Linux)
    │  asyncio (fallback)  │ ← standard selector loop
    └──────────────────────┘

Usage:
    from cortex.event_loop import sovereign_run

    # Replace: asyncio.run(coro())
    # With:    sovereign_run(coro())
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, TypeVar

__all__ = ["install_uvloop", "sovereign_run"]

logger = logging.getLogger("cortex.event_loop")

T = TypeVar("T")

_uvloop_installed = False


def install_uvloop() -> bool:
    """Check if uvloop is available (deprecated — use sovereign_run() instead).

    .. deprecated:: 5.2
        This function previously called ``asyncio.set_event_loop_policy()``
        which is deprecated in Python 3.16. Use ``sovereign_run()`` instead,
        which calls ``uvloop.run()`` directly without policy manipulation.

    Returns True if uvloop is available, False otherwise.
    Safe to call multiple times (idempotent).
    """
    global _uvloop_installed  # noqa: PLW0603

    if _uvloop_installed:
        return True

    try:
        import uvloop  # type: ignore[import-untyped]

        _uvloop_installed = True
        logger.info(
            "Sovereign loop: uvloop %s detected (use sovereign_run() for activation)",
            getattr(uvloop, "__version__", "?"),
        )
        return True
    except ImportError:
        logger.debug("uvloop not available, using stdlib asyncio loop")
        return False


def sovereign_run(
    coro: Any,
    *,
    debug: bool = False,
) -> T:
    """Run a coroutine with the sovereign event loop (uvloop if available).

    Drop-in replacement for asyncio.run() that:
    1. Uses uvloop.run() directly when available (Python 3.16 safe)
    2. Falls back to asyncio.run() otherwise
    3. Provides consistent logging

    Args:
        coro: The coroutine to run.
        debug: Enable asyncio debug mode.

    Returns:
        The result of the coroutine.
    """
    global _uvloop_installed  # noqa: PLW0603

    try:
        import uvloop  # type: ignore[import-untyped]

        if not _uvloop_installed:
            _uvloop_installed = True
            logger.info(
                "Sovereign loop: uvloop %s active (kqueue/epoll)",
                getattr(uvloop, "__version__", "?"),
            )
        # uvloop.run() creates its own loop — no policy needed (3.16 safe)
        return uvloop.run(coro, debug=debug)
    except ImportError:
        return asyncio.run(coro, debug=debug)


def get_loop_info() -> dict[str, Any]:
    """Return information about the current event loop configuration."""
    info: dict[str, Any] = {
        "uvloop_installed": _uvloop_installed,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
    }

    try:
        loop = asyncio.get_running_loop()
        info["loop_class"] = type(loop).__name__
        info["loop_running"] = loop.is_running()
    except RuntimeError:
        info["loop_class"] = None
        info["loop_running"] = False

    return info
