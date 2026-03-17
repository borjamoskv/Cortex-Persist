"""
Reflex Engine - Autonomic Responses and Immune Defense.
Ω₅: High adrenaline triggers diagnostic healing.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.extensions.signals.bus import SignalBus

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
        from cortex.database.core import connect

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
                            from cortex.engine.keter import KeterEngine

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
    from cortex.engine.keter import KeterEngine

    keter = KeterEngine()
    try:
        await keter.ignite("Sovereign Immune Reflex (Ω₅).", workspace=workspace)
    except (OSError, ValueError, asyncio.CancelledError) as e:
        logger.warning("[REFLEX] Fallback reflex aborted: %s", e)
