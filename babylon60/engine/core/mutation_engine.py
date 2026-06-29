# [C5-REAL] Exergy-Maximized
"""Solid-State Mutation Engine (CQRS Write Gateway).

The ONLY sanctioned write path for fact state changes.

Reality Level: C5-REAL
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from babylon60.engine.evo._mutation_projectors import project
from babylon60.extensions.axioms.topological_id import flake_gen

__all__ = ["FactMutationEngine"]
logger = logging.getLogger("cortex.mutation_engine")

_PAYLOAD_SCHEMA_VERSION = "1"
_FACT_COLUMNS_CACHE: dict[int, set[str]] = {}
_ROLLBACK_ERRORS = (
    aiosqlite.Error,
    AssertionError,
    KeyError,
    LookupError,
    PermissionError,
    RuntimeError,
    TypeError,
    ValueError,
)


class FactMutationEngine:
    """Solid-State Write Gateway for CORTEX facts."""

    async def apply(
        self,
        conn: aiosqlite.Connection,
        *,
        fact_id: int,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        signer: str = "",
        commit: bool = True,
    ) -> str:
        """Append an immutable event and project its effect atomically."""
        event_id = flake_gen.next_lexicographic_id()
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, default=str)

        # ── 1. Hash-chain: link to the last event for this entity ────
        prev_hash = await self._get_last_hash(conn, fact_id)
        chain_input = f"{event_id}:{fact_id}:{tenant_id}:{event_type}:{payload_str}:{prev_hash}"
        signature = hashlib.sha3_256(chain_input.encode()).hexdigest()

        # ── 2. Atomic transaction: INSERT event + UPDATE projection ──
        try:
            await conn.execute(
                "INSERT INTO entity_events "
                "(id, entity_id, tenant_id, event_type, payload, "
                "timestamp, prev_hash, signature, signer, schema_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    fact_id,
                    tenant_id,
                    event_type,
                    payload_str,
                    ts,
                    prev_hash,
                    signature,
                    signer,
                    _PAYLOAD_SCHEMA_VERSION,
                ),
            )
            # ── 3. Project mutation into facts (materialized view) ───────
            await project(self, conn, fact_id, tenant_id, event_type, payload)
            if commit:
                await conn.commit()
        except _ROLLBACK_ERRORS:
            await conn.rollback()
            raise

        logger.debug(
            "Solid-state event %s: entity=%d type=%s signer=%s",
            event_id,
            fact_id,
            event_type,
            signer,
        )
        return event_id

    # ── Hash-Chain ───────────────────────────────────────────────────
    async def _get_last_hash(
        self,
        conn: aiosqlite.Connection,
        entity_id: int,
    ) -> str:
        """Fetch the signature of the most recent event for this entity."""
        async with conn.execute(
            "SELECT signature FROM entity_events WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
            (entity_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else "GENESIS"

    async def _get_fact_tenant_id(self, conn: aiosqlite.Connection, fact_id: int) -> str:
        """Resolve the tenant_id for a fact from the materialized view."""
        async with conn.execute("SELECT tenant_id FROM facts WHERE id = ?", (fact_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row and row[0] else "default"

    async def _facts_columns(self, conn: aiosqlite.Connection) -> set[str]:
        """Return the facts schema columns for the current connection."""
        cache_key = id(conn)
        cached = _FACT_COLUMNS_CACHE.get(cache_key)
        if cached is not None:
            return cached
        async with conn.execute("PRAGMA table_info(facts)") as cursor:
            rows = await cursor.fetchall()
        columns = {str(row[1]) for row in rows}
        _FACT_COLUMNS_CACHE[cache_key] = columns
        return columns

    async def _metadata_column(self, conn: aiosqlite.Connection) -> str | None:
        """Resolve the metadata column name across legacy schemas."""
        columns = await self._facts_columns(conn)
        if "metadata" in columns:
            return "metadata"
        if "meta" in columns:
            return "meta"
        return None


# ── Module-level singleton ───────────────────────────────────────────
MUTATION_ENGINE = FactMutationEngine()
