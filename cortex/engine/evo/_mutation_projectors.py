# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.flow.causality import AsyncCausalGraph

if TYPE_CHECKING:
    from cortex.engine.core.mutation_engine import FactMutationEngine

logger = logging.getLogger("cortex.mutation_engine")


async def project(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Update the facts materialized view based on event type."""
    _PROJECTORS = {
        "deprecate": proj_deprecate,
        "tombstone": proj_tombstone,
        "archaeology_merge": proj_archaeology_merge,
        "quarantine": proj_quarantine,
        "unquarantine": proj_unquarantine,
        "mutate_to_ghost": proj_mutate_to_ghost,
        "reparent": proj_reparent,
        "score_update": proj_score_update,
        "taint_update": proj_taint_update,
        "decalcify": proj_decalcify,
        "restore": proj_restore,
    }
    projector = _PROJECTORS.get(event_type)
    if projector:
        if event_type in {
            "tombstone",
            "archaeology_merge",
            "quarantine",
            "taint_update",
            "reparent",
        }:
            await projector(engine, conn, fact_id, payload, tenant_id=tenant_id)
        else:
            await projector(engine, conn, fact_id, payload)
    else:
        # Unknown event type - log but don't fail.
        logger.info(
            "No projector for event_type=%s on fact %d - event stored but not projected",
            event_type,
            fact_id,
        )


async def proj_decalcify(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    """Protocol Ω₃-E: Reduce certainty over time to prevent stagnation."""
    decay_factor = payload.get("decay_factor", 0.95)
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    facts_columns = await engine._facts_columns(conn)
    has_consensus_column = "consensus_score" in facts_columns
    # 1. Fetch current scores
    score_query = (
        "SELECT consensus_score, confidence FROM facts WHERE id = ?"
        if has_consensus_column
        else "SELECT json_extract(metadata, '$.consensus_score'), confidence FROM facts WHERE id = ?"
    )
    async with conn.execute(score_query, (fact_id,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return
    current_score_raw, confidence = row
    current_score = float(current_score_raw) if current_score_raw is not None else 1.0
    new_score = round(current_score * decay_factor, 3)
    # 2. State demotion (Verified -> Tentative -> Disputed)
    new_confidence = confidence
    if new_score < 1.4 and confidence == "verified":
        new_confidence = "tentative"
    elif new_score < 0.6 and confidence != "disputed":
        new_confidence = "disputed"
    if has_consensus_column:
        await conn.execute(
            "UPDATE facts SET confidence = ?, updated_at = ?, consensus_score = ? WHERE id = ?",
            (new_confidence, ts, new_score, fact_id),
        )
        return
    query = (
        "UPDATE facts SET confidence = ?, updated_at = ?, "
        "metadata = CASE "
        "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
        "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
        "END "
        "WHERE id = ?"
    )
    await conn.execute(query, (new_confidence, ts, new_score, fact_id))


async def proj_deprecate(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    reason = payload.get("reason", "deprecated")
    await conn.execute(
        "UPDATE facts SET valid_until = ?, updated_at = ?, "
        "metadata = CASE "
        "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
        "  ELSE json_set(COALESCE(metadata, '{}'), '$.deprecation_reason', ?) "
        "END "
        "WHERE id = ?",
        (ts, ts, reason, fact_id),
    )


async def proj_mutate_to_ghost(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    """Project an evaporation event into ghost state."""
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "UPDATE facts SET fact_type = 'ghost', updated_at = ? WHERE id = ?",
        (ts, fact_id),
    )


async def proj_tombstone(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
    tenant_id: str | None = None,
) -> None:
    reason = payload.get("reason", "tombstoned")
    ts = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
    query = (
        "UPDATE facts SET valid_until = ?, is_tombstoned = 1, updated_at = ?, "
        "metadata = CASE "
        "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
        "  ELSE json_set(COALESCE(metadata, '{}'), '$.tombstoned_at', ?, "
        "                '$.tombstone_reason', ?) "
        "END "
        "WHERE id = ?"
    )
    await conn.execute(query, (ts, ts, ts, reason, fact_id))
    resolved_tenant_id = tenant_id or await engine._get_fact_tenant_id(conn, fact_id)
    graph = AsyncCausalGraph(conn)
    report = await graph.propagate_taint(fact_id, tenant_id=resolved_tenant_id)
    logger.info(
        "Ω₁₃ Taint (Tombstone) propagated from fact %d: %d nodes affected",
        fact_id,
        report.affected_count,
    )


async def proj_archaeology_merge(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
    tenant_id: str | None = None,
) -> None:
    """Archive a superseded fact without treating it as invalidated/tainted."""
    ts = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
    reason = payload.get("reason", "archaeology-merged")
    replacement_fact_id = payload.get("replacement_fact_id")
    metadata_column = await engine._metadata_column(conn)
    query = "UPDATE facts SET valid_until = ?, is_tombstoned = 1"
    params: list[Any] = [ts]
    facts_columns = await engine._facts_columns(conn)
    if "updated_at" in facts_columns:
        query += ", updated_at = ?"
        params.append(ts)
    if metadata_column:
        query += (
            f", {metadata_column} = CASE "
            f"  WHEN {metadata_column} LIKE 'v6_aesgcm:%' THEN {metadata_column} "
            f"  ELSE json_set(COALESCE({metadata_column}, '{{}}'), "
            "                '$.tombstoned_at', ?, "
            "                '$.tombstone_reason', ?, "
            "                '$.archaeology_replacement_fact_id', ?) "
            "END"
        )
        params.extend([ts, reason, replacement_fact_id])
    query += " WHERE id = ?"
    params.append(fact_id)
    if "tenant_id" in facts_columns:
        query += " AND tenant_id = ?"
        params.append(tenant_id or await engine._get_fact_tenant_id(conn, fact_id))
    await conn.execute(query, tuple(params))


async def proj_quarantine(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
    tenant_id: str | None = None,
) -> None:
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    reason = payload.get("reason", "quarantined")
    await conn.execute(
        "UPDATE facts SET is_quarantined = 1, quarantined_at = ?, "
        "quarantine_reason = ?, updated_at = ? "
        "WHERE id = ?",
        (ts, reason, ts, fact_id),
    )
    resolved_tenant_id = tenant_id or await engine._get_fact_tenant_id(conn, fact_id)
    graph = AsyncCausalGraph(conn)
    report = await graph.propagate_taint(fact_id, tenant_id=resolved_tenant_id)
    logger.info(
        "Ω₁₃ Taint (Quarantine) propagated from fact %d: %d nodes affected",
        fact_id,
        report.affected_count,
    )


async def proj_unquarantine(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "UPDATE facts SET is_quarantined = 0, quarantined_at = NULL, "
        "quarantine_reason = NULL, updated_at = ? WHERE id = ?",
        (ts, fact_id),
    )


async def proj_score_update(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    score = payload.get("consensus_score")
    confidence = payload.get("confidence")
    facts_columns = await engine._facts_columns(conn)
    has_consensus_column = "consensus_score" in facts_columns
    if has_consensus_column and score is not None and confidence is not None:
        await conn.execute(
            "UPDATE facts SET confidence = ?, consensus_score = ? WHERE id = ?",
            (confidence, score, fact_id),
        )
    elif has_consensus_column and score is not None:
        await conn.execute(
            "UPDATE facts SET consensus_score = ? WHERE id = ?",
            (score, fact_id),
        )
    elif confidence is not None and score is None:
        await conn.execute(
            "UPDATE facts SET confidence = ? WHERE id = ?",
            (confidence, fact_id),
        )
    elif score is not None and confidence is not None:
        await conn.execute(
            "UPDATE facts SET confidence = ?, "
            "metadata = CASE "
            "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
            "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
            "END "
            "WHERE id = ?",
            (confidence, score, fact_id),
        )
    elif score is not None:
        await conn.execute(
            "UPDATE facts SET "
            "metadata = CASE "
            "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
            "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
            "END "
            "WHERE id = ?",
            (score, fact_id),
        )
    elif confidence is not None:
        await conn.execute(
            "UPDATE facts SET confidence = ? WHERE id = ?",
            (confidence, fact_id),
        )


async def _update_metadata(
    conn: aiosqlite.Connection,
    fact_id: int,
    tenant_id: str,
    metadata_column: str,
    updates: dict,
) -> str | None:
    async with conn.execute(
        f"SELECT {metadata_column} FROM facts WHERE id = ?", (fact_id,)
    ) as cursor:
        row = await cursor.fetchone()
    raw_meta = row[0] if row else None
    if raw_meta:
        encrypter = get_default_encrypter()
        if isinstance(raw_meta, str) and raw_meta.startswith(encrypter.PREFIX):
            meta = encrypter.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
            meta.update(updates)
            return encrypter.encrypt_json(meta, tenant_id=tenant_id)
        else:
            try:
                meta = json.loads(raw_meta)
            except (TypeError, json.JSONDecodeError):
                return None
            else:
                meta.update(updates)
                return json.dumps(meta)
    elif raw_meta in ("", None):
        return json.dumps(updates)
    return None


async def proj_taint_update(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
    tenant_id: str | None = None,
) -> None:
    resolved_tenant_id = tenant_id or await engine._get_fact_tenant_id(conn, fact_id)
    confidence = payload.get("confidence")
    metadata_column = await engine._metadata_column(conn)
    facts_columns = await engine._facts_columns(conn)
    metadata_value: str | None = None
    if metadata_column:
        updates = {
            "taint_status": payload["taint_status"],
            "tainted_by": payload["tainted_by"],
            "taint_timestamp": payload["taint_timestamp"],
        }
        metadata_value = await _update_metadata(
            conn, fact_id, resolved_tenant_id, metadata_column, updates
        )
    set_clauses: list[str] = []
    params: list[Any] = []
    if confidence is not None:
        set_clauses.append("confidence = ?")
        params.append(confidence)
    if metadata_column and metadata_value is not None:
        set_clauses.append(f"{metadata_column} = ?")
        params.append(metadata_value)
    if "updated_at" in facts_columns:
        set_clauses.append("updated_at = ?")
        params.append(payload.get("taint_timestamp") or datetime.now(timezone.utc).isoformat())
    if not set_clauses:
        return
    query = f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ?"
    params.append(fact_id)
    if "tenant_id" in facts_columns:
        query += " AND tenant_id = ?"
        params.append(resolved_tenant_id)
    await conn.execute(query, tuple(params))


async def proj_reparent(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
    tenant_id: str | None = None,
) -> None:
    resolved_tenant_id = tenant_id or await engine._get_fact_tenant_id(conn, fact_id)
    new_parent = payload.get("parent_decision_id")
    if new_parent is None:
        return
    facts_columns = await engine._facts_columns(conn)
    metadata_column = await engine._metadata_column(conn)
    set_clauses: list[str] = []
    params: list[Any] = []
    if "parent_decision_id" in facts_columns:
        set_clauses.append("parent_decision_id = ?")
        params.append(new_parent)
    if "parent_id" in facts_columns:
        set_clauses.append("parent_id = ?")
        params.append(new_parent)
    metadata_value: str | None = None
    if (
        metadata_column
        and "parent_decision_id" not in facts_columns
        and "parent_id" not in facts_columns
    ):
        metadata_value = await _update_metadata(
            conn, fact_id, resolved_tenant_id, metadata_column, {"parent_decision_id": new_parent}
        )
    if metadata_column and metadata_value is not None:
        set_clauses.append(f"{metadata_column} = ?")
        params.append(metadata_value)
    if "updated_at" in facts_columns:
        set_clauses.append("updated_at = ?")
        params.append(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
    if not set_clauses:
        return
    query = f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ?"
    params.append(fact_id)
    if "tenant_id" in facts_columns:
        query += " AND tenant_id = ?"
        params.append(resolved_tenant_id)
    await conn.execute(query, tuple(params))


async def proj_restore(
    engine: FactMutationEngine,
    conn: aiosqlite.Connection,
    fact_id: int,
    payload: dict,
) -> None:
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "UPDATE facts SET valid_until = NULL, is_tombstoned = 0, "
        "tombstoned_at = NULL, is_quarantined = 0, quarantined_at = NULL, "
        "quarantine_reason = NULL, updated_at = ? WHERE id = ?",
        (ts, fact_id),
    )
