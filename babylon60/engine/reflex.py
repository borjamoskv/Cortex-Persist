# [C5-REAL] Exergy-Maximized
"""
Reflex Engine - Autonomic Responses and Immune Defense.
Ω₅: High adrenaline triggers diagnostic healing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

from babylon60.engine.endocrine import ENDOCRINE, HormoneType
from babylon60.extensions.signals.bus import SignalBus

logger = logging.getLogger(__name__)


async def trigger_autonomic_reflex(
    workspace: Path,
    cortex_engine: Any,
    active_tasks: set[asyncio.Task],
    signal_bus: SignalBus | None = None,
) -> None:
    """Sovereign Reflex: High adrenaline triggers a diagnostic healing sweep."""
    if not cortex_engine:
        return

    # Avoid redundant reflex if a task for the same reason is still active
    active_reflex_reasons = {getattr(t, "_reflex_reason", "") for t in active_tasks}

    logger.warning(
        "[REFLEX] Autonomic Reflex Triggered (Ω₅). Current active: %d", len(active_reflex_reasons)
    )

    try:
        from babylon60.database.core import connect

        db_path = getattr(cortex_engine, "_db_path", None)
        if db_path:
            # We use a dedicated thread/connection for the reflex scan if needed
            # but usually we can reuse the engine context or a fresh connection
            with connect(str(db_path)) as conn:
                bus = SignalBus(conn)
                recent = bus.peek(event_type="nemesis:rejection", limit=5)

                if recent:
                    for signal in recent:
                        target = signal.payload.get("file")
                        reason = signal.payload.get("reason", "Unknown Entropia")

                        if reason in active_reflex_reasons:
                            continue

                        if target:
                            logger.warning("🎯 [REFLEX] Targeted Reflex: %s", target)
                            from babylon60.engine.keter import KeterEngine

                            keter = KeterEngine()
                            reflex_task = asyncio.create_task(
                                keter.ignite(
                                    f"Eliminate antibody vector in {target}: {reason}",
                                    workspace=workspace,
                                )
                            )
                            reflex_task._reflex_reason = reason  # type: ignore[reportAttributeAccessIssue]
                            active_tasks.add(reflex_task)
                            reflex_task.add_done_callback(active_tasks.discard)
                            return
    except (aiosqlite.Error, OSError, KeyError) as e:
        logger.error("[REFLEX] Reflex failure: %s", e)

    ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1)
    from babylon60.engine.keter import KeterEngine

    keter = KeterEngine()
    try:
        await keter.ignite("Sovereign Immune Reflex (Ω₅).", workspace=workspace)
    except (OSError, ValueError, asyncio.CancelledError) as e:
        logger.warning("[REFLEX] Fallback reflex aborted: %s", e)
