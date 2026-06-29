# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import aiosqlite

from babylon60.engine.flow.causality import AsyncCausalGraph
from babylon60.utils.canonical import now_iso
from babylon60.database.core import causal_write

logger = logging.getLogger("cortex.store_mutation")


async def _fetch_fact_state(
    conn: aiosqlite.Connection, fact_id: int, tenant_id: str
) -> aiosqlite.Row | tuple[Any, ...] | None:
    cursor = await conn.execute(
        """
        SELECT tenant_id, fact_type, valid_until, is_tombstoned, is_quarantined
        FROM facts
        WHERE id = ? AND tenant_id = ?
        """,
        (fact_id, tenant_id),
    )
    return await cursor.fetchone()


async def deprecate_impl_logic(
    *,
    mixin_instance: Any,
    conn: aiosqlite.Connection,
    fact_id: int,
    reason: str | None,
    tenant_id: str,
) -> bool:
    row = await _fetch_fact_state(conn, fact_id, tenant_id)
    if not row or row[2] is not None:
        return False

    ts = now_iso()
    with causal_write(conn):
        await conn.execute(
            """
            UPDATE facts
            SET valid_until = ?, updated_at = ?,
                metadata = CASE
                    WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata
                    ELSE json_set(COALESCE(metadata, '{}'), '$.deprecation_reason', ?)
                END
            WHERE id = ? AND tenant_id = ?
            """,
            (ts, ts, reason or "deprecated", fact_id, tenant_id),
        )
    await mixin_instance._log_transaction(
        conn,
        "system",
        "deprecate",
        {"fact_id": fact_id, "reason": reason or "deprecated", "timestamp": ts},
        tenant_id=tenant_id,
    )

    # Ω₁₃: Deprecation should degrade descendants just like invalidation.
    graph = AsyncCausalGraph(conn)
    await graph.propagate_taint(fact_id, tenant_id=tenant_id, floor_to_c1=False)
    return True


async def invalidate_impl_logic(
    *,
    mixin_instance: Any,
    conn: aiosqlite.Connection,
    fact_id: int,
    reason: str | None,
    tenant_id: str,
) -> bool:
    row = await _fetch_fact_state(conn, fact_id, tenant_id)
    if not row or bool(row[3]):
        return False

    ts = now_iso()
    with causal_write(conn):
        await conn.execute(
            """
            UPDATE facts
            SET valid_until = ?, is_tombstoned = 1, confidence = 'C1', updated_at = ?,
                metadata = CASE
                    WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata
                    ELSE json_set(
                        COALESCE(metadata, '{}'),
                        '$.tombstoned_at', ?,
                        '$.tombstone_reason', ?
                    )
                END
            WHERE id = ? AND tenant_id = ?
            """,
            (ts, ts, ts, reason or "invalidated", fact_id, tenant_id),
        )
    await mixin_instance._log_transaction(
        conn,
        "system",
        "invalidate",
        {"fact_id": fact_id, "reason": reason or "invalidated", "timestamp": ts},
        tenant_id=tenant_id,
    )

    # Ω₁₃: Invalidation must cascade taint to descendants.
    graph = AsyncCausalGraph(conn)
    await graph.propagate_taint(fact_id, tenant_id=tenant_id, floor_to_c1=False)
    return True


async def _delete_best_effort(
    conn: aiosqlite.Connection,
    statement: str,
    params: tuple[Any, ...],
) -> None:
    try:
        with causal_write(conn):
            await conn.execute(statement, params)
    except (sqlite3.Error, aiosqlite.Error) as exc:
        if "no such table" not in str(exc).lower():
            raise


async def purge_logic(
    *,
    mixin_instance: Any,
    fact_id: int,
    tenant_id: str,
    force: bool,
) -> bool:
    async with mixin_instance.session() as conn:
        row = await _fetch_fact_state(conn, fact_id, tenant_id)
        if not row:
            return False

        fact_type = row[1] or "knowledge"

        child_count = 0
        try:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM causal_edges WHERE parent_id = ? AND tenant_id = ?",
                (fact_id, tenant_id),
            )
            count_row = await cursor.fetchone()
            child_count = int(count_row[0]) if count_row else 0
        except (sqlite3.Error, aiosqlite.Error):
            child_count = 0

        base_criticality = 0.5 if fact_type == "rule" else 0.0
        dependency_criticality = min(0.4, child_count * 0.1)
        criticality = base_criticality + dependency_criticality

        if criticality > 0.8 and not force:
            raise RuntimeError("Bounded Demolition Denied: criticality > 0.8")

        # Fetch the hash and tx_id of the fact before purging
        cursor = await conn.execute(
            "SELECT hash, tx_id FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        fact_info = await cursor.fetchone()

        fact_hash = fact_info[0] if fact_info else None
        store_tx_id = fact_info[1] if fact_info else None

        await mixin_instance._log_transaction(
            conn,
            "system",
            "purge",
            {
                "fact_id": fact_id,
                "force": force,
                "timestamp": now_iso(),
                "content_hash": fact_hash,
                "store_tx_id": store_tx_id,
            },
            tenant_id=tenant_id,
        )

        delete_specs = [
            ("DELETE FROM fact_tags WHERE fact_id = ? AND tenant_id = ?", (fact_id, tenant_id)),
            ("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,)),
            ("DELETE FROM specular_embeddings WHERE fact_id = ?", (fact_id,)),
            ("DELETE FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)),
            (
                "DELETE FROM entity_events WHERE entity_id = ? AND tenant_id = ?",
                (fact_id, tenant_id),
            ),
            (
                "DELETE FROM causal_edges WHERE (fact_id = ? OR parent_id = ?) AND tenant_id = ?",
                (fact_id, fact_id, tenant_id),
            ),
            # FTS cleanup is explicit because facts.content is encrypted in the
            # primary table and trigger-driven sync is not reliable for writes.
            ("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,)),
        ]
        for statement, params in delete_specs:
            await _delete_best_effort(conn, statement, params)

        with causal_write(conn):
            cursor = await conn.execute(
                "DELETE FROM facts WHERE id = ? AND tenant_id = ?",
                (fact_id, tenant_id),
            )
        await conn.commit()
        return cursor.rowcount > 0
