# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.database.core import connect
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

try:
    from cortex.engine.logic.atms import AtmsAdapter
except ImportError:
    AtmsAdapter = None  # type: ignore

logger = logging.getLogger("cortex.engine.causality")


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(tenant_id=tenant_id, project=project, limit=5)
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except (sqlite3.Error, ValueError, RuntimeError) as e:
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
    def find_parent_signal(
        db_path: str,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        try:
            with connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(tenant_id=tenant_id, project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except (sqlite3.Error, ValueError, RuntimeError) as e:
            logger.debug("Sync causal lookup failed: %s", e)
        return None


def link_causality(
    meta: dict[str, Any] | None,
    signal_id: int | None,
) -> dict[str, Any]:
    """Attach causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m


def rowless_json(data: dict[str, Any]) -> str:
    return json.dumps(data)
