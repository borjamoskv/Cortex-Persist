"""
Kinetic Response Engine - Autonomic Reactions and Quarantine Defense.
Ω₅: High pressure triggers diagnostic healing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.engine.gradient import GRADIENT, GradientType
from cortex.extensions.signals.bus import SignalBus

logger = logging.getLogger(__name__)


async def trigger_kinetic_response(
    workspace: Path,
    cortex_engine: Any,
    active_tasks: set[asyncio.Task],
    signal_bus: SignalBus | None = None,
) -> None:
    """Sovereign Kinetic Response: High pressure triggers a diagnostic quarantine sweep."""
    if not cortex_engine:
        return

    # Avoid redundant response if a task for the same reason is still active
    active_response_reasons = {getattr(t, "_response_reason", "") for t in active_tasks}

    logger.warning(
        "[KINETIC] Autonomic Response Triggered (Ω₅). Current active: %d",
        len(active_response_reasons),
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

                        if reason in active_response_reasons:
                            continue

                        if target:
                            logger.warning("🎯 [KINETIC] Targeted Response: %s", target)
                            from cortex.engine.keter import KeterEngine

                            keter = KeterEngine()
                            response_task = asyncio.create_task(
                                keter.ignite(
                                    f"Eliminate quarantine vector in {target}: {reason}",
                                    workspace=workspace,
                                )
                            )
                            response_task._response_reason = reason  # type: ignore[reportAttributeAccessIssue]
                            active_tasks.add(response_task)
                            response_task.add_done_callback(active_tasks.discard)
                            return
    except (aiosqlite.Error, OSError, KeyError) as e:
        logger.error("[KINETIC] Response failure: %s", e)

    GRADIENT.pulse(GradientType.PRESSURE, 0.1)
    from cortex.engine.keter import KeterEngine

    keter = KeterEngine()
    try:
        await keter.ignite("Sovereign Kinetic Response (Ω₅).", workspace=workspace)
    except (OSError, ValueError, asyncio.CancelledError) as e:
        logger.warning("[KINETIC] Fallback response aborted: %s", e)
