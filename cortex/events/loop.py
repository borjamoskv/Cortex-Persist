# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Sovereign Event Loop (KETER-∞ Ola 2).

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
from cortex.ipc.server import IPCServer

__all__ = ["install_uvloop", "sovereign_run", "get_loop_info", "start_glial_daemon", "stop_glial_daemon"]

logger = logging.getLogger("cortex.event_loop")

T = TypeVar("T")

_uvloop_installed = False


def install_uvloop() -> bool:
    """Check if uvloop is available (deprecated - use sovereign_run() instead).

    .. deprecated:: 5.2
        This function previously called ``asyncio.set_event_loop_policy()``
        which is deprecated in Python 3.16. Use ``sovereign_run()`` instead,
        which calls ``uvloop.run()`` directly without policy manipulation.

    Returns True if uvloop is available, False otherwise.
    Safe to call multiple times (idempotent).
    """
    global _uvloop_installed

    if _uvloop_installed:
        return True

    try:
        import uvloop  # type: ignore[import-untyped]

        _uvloop_installed = True
        logger.info(
            "Sovereign loop: uvloop %s detected (activation delegated to sovereign_run)",
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
) -> Any:
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
    global _uvloop_installed

    # 1. Detect loop capability first (cached)
    has_uvloop = False
    try:
        import uvloop  # type: ignore[import-untyped]

        has_uvloop = True
        if not _uvloop_installed:
            _uvloop_installed = True
            logger.info(
                "Sovereign loop: uvloop %s active (kqueue/epoll)",
                getattr(uvloop, "__version__", "?"),
            )
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)

    # 2. Execute with appropriate runner
    if has_uvloop:
        import uvloop  # type: ignore[import-untyped]

        return uvloop.run(coro, debug=debug)
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

async def start_glial_daemon(engine) -> None:
    """Start the Glial Daemon IPC server for single-writer enforcement.

    Args:
        engine: The Cortex engine instance that the IPC server will use to
            forward store requests.
    """
    ipc_server = IPCServer(engine=engine)
    globals()["_glial_ipc_server"] = ipc_server
    await ipc_server.start()
    
    async def daemon_run_loop():
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(daemon_run_loop())
    globals()["_glial_ipc_task"] = task
    engine._glial_daemon_task = task

async def stop_glial_daemon() -> None:
    """Stop the Glial Daemon IPC server if it is running."""
    server = globals().get("_glial_ipc_server")
    task = globals().get("_glial_ipc_task")
    if server:
        if hasattr(server.engine, "_glial_daemon_task"):
            delattr(server.engine, "_glial_daemon_task")
        await server.stop()
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    globals().pop("_glial_ipc_server", None)
    globals().pop("_glial_ipc_task", None)
