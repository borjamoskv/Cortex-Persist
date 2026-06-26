# [C5-REAL] Exergy-Maximized
"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex")


async def _get_table_columns(conn: aiosqlite.Connection, table_name: str) -> set[str]:
    """Return the set of column names for a SQLite table."""
    async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
        rows = await cursor.fetchall()
    return {str(row[1]) for row in rows}


async def _prepare_fact_content(
    content: str, tenant_id: str
) -> tuple[str, str, str | None, str | None]:
    """Encrypted content and cryptographic signatures."""
    from cortex.crypto import get_default_encrypter
    from cortex_extensions.security.signatures import get_default_signer

    f_hash = compute_fact_hash(content)
    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)

    sig_b64, pub_b64 = None, None
    try:
        signer = get_default_signer()
        if signer and signer.can_sign:
            sig_b64 = signer.sign(content, f_hash)
            pub_b64 = signer.public_key_b64
    except (ImportError, ValueError, OSError) as e:
        logger.debug("Fact signing skipped: %s", e)

    return f_hash, encrypted_content, sig_b64, pub_b64  # pyright: ignore[reportReturnType]


async def _resolve_causal_parent(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    fact_type: str,
    parent_decision_id: int | None,
) -> int | None:
    """Validate or auto-resolve the parent decision link."""
    if parent_decision_id is not None:
        async with conn.execute(
            "SELECT id FROM facts WHERE id = ? AND tenant_id = ?",
            (parent_decision_id, tenant_id),
        ) as cursor:
            if await cursor.fetchone() is None:
                raise ValueError(
                    f"parent_decision_id={parent_decision_id} is missing or cross-tenant"
                )
        return parent_decision_id

    if fact_type in ("decision", "error"):
        async with conn.execute(
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ? "
            "AND fact_type = 'decision' AND is_tombstoned = 0 "
            "ORDER BY id DESC LIMIT 1",
            (project, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            logger.debug("Auto-resolved parent=%d for %s", row[0], fact_type)
            return row[0]
    return None


async def insert_fact_record(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    content: str,
    fact_type: str,
    tags: list[str] | None,
    confidence: str,
    ts: str | None,
    source: str | None,
    meta: dict[str, Any] | None,
    tx_id: int | None,
    parent_decision_id: int | None = None,
    taint_already_verified: bool = False,
) -> int:
    """Perform the actual SQL insert into the facts table."""
    ts = ts or now_iso()
    tags_json = json.dumps(tags or [])

    from cortex.engine.causal.taint_engine import enforce_taint_check
    from cortex.guards.secret_guard import SecretGuard

    # Enforce OWASP LLM06 Secret Redaction before any persistence
    SecretGuard.verify_clean(content)

    # Edge sensor telemetry is authenticated via X-Cortex-Source header, not taint tokens
    if not taint_already_verified and fact_type not in ("telemetry_batch", "mafia_node"):
        token = meta.get("cortex_taint") if meta else None
        await enforce_taint_check(conn, token, content)

    if fact_type == "UI_ACTION" and meta:
        expected_hash = meta.get("expected_ui_hash")
        current_hash = meta.get("current_ui_hash")
        if expected_hash is not None and current_hash is not None:
            from cortex.guards.ctre_guard import CTRECollisionError, CTREGuard

            success, epsilon = CTREGuard.validate_commit(int(expected_hash), int(current_hash))
            if not success:
                raise CTRECollisionError(int(expected_hash), int(current_hash), epsilon)

    f_hash, encrypted_content, sig_b64, pub_b64 = await _prepare_fact_content(content, tenant_id)

    parent_decision_id = await _resolve_causal_parent(
        conn, tenant_id, project, fact_type, parent_decision_id
    )

    # 3. SQL Persistence
    payload = await _build_fact_payload(
        conn,
        tenant_id,
        project,
        encrypted_content,
        fact_type,
        meta,  # pyright: ignore[reportArgumentType]
        f_hash,
        source,
        confidence,
        parent_decision_id,
        tx_id,
        tags_json,
        ts,
    )

    columns_sql = ", ".join(column for column, _ in payload)
    placeholders_sql = ", ".join("?" for _ in payload)
    values = [value for _, value in payload]

    async with conn.execute(
        f"INSERT INTO facts ({columns_sql}) VALUES ({placeholders_sql})",
        values,
    ) as cursor:
        fact_id = cursor.lastrowid
    assert fact_id is not None

    await _post_insert_actions(
        conn,
        fact_id,
        content,
        tenant_id,
        project,
        tags,
        tags_json,
        fact_type,
        ts,
        meta,  # pyright: ignore[reportArgumentType]
        parent_decision_id,
    )

    return fact_id


async def _build_fact_payload(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    encrypted_content: str,
    fact_type: str,
    meta: dict[str, Any],
    f_hash: str,
    source: str | None,
    confidence: str,
    parent_decision_id: int | None,
    tx_id: int | None,
    tags_json: str,
    ts: str,
) -> list[tuple[str, Any]]:
    """Construct the SQL payload with layout-aware column detection."""
    from cortex.engine.meta.metadata_engine import MetadataEngine
    from cortex.engine.uncategorized.models import Fact

    temp_fact = Fact(
        id=0,
        tenant_id=tenant_id,
        project=project,
        content="",
        fact_type=fact_type,
        tags=[],
        parent_id=parent_decision_id,
        relation_type=meta.get("relation_type"),
    )
    m2 = MetadataEngine.classify_deterministic(temp_fact)

    rank_map = {"C5": 5, "C4": 4, "C3": 3, "C2": 2, "C1": 1, "stated": 5, "verified": 5}
    c_rank = rank_map.get(confidence, 3)

    facts_columns = await _get_table_columns(conn, "facts")
    payload: list[tuple[str, Any]] = []

    def add(col: str, val: Any) -> None:
        if col in facts_columns:
            payload.append((col, val))

    add("tenant_id", tenant_id)
    add("project", project)
    add("content", encrypted_content)
    add("fact_type", fact_type)

    meta_json = json.dumps(meta)
    if "metadata" in facts_columns:
        add("metadata", meta_json)
    elif "meta" in facts_columns:
        add("meta", meta_json)

    add("hash", f_hash)
    add("source", source)
    add("confidence", confidence)
    add("confidence_rank", c_rank)
    add("consensus_score", float(meta.get("consensus_score", 1.0)))
    if "parent_id" in facts_columns:
        add("parent_id", parent_decision_id)
    elif "parent_decision_id" in facts_columns:
        add("parent_decision_id", parent_decision_id)

    add("relation_type", m2["relation_type"])
    add("quadrant", m2["quadrant"])
    add("storage_tier", m2["storage_tier"])
    add("exergy_score", m2["exergy_score"])
    add("category", m2["category"])
    add("yield_score", m2["yield_score"])
    add("semantic_status", "pending")
    add("tags", tags_json)
    add("tx_id", tx_id)
    add("created_at", ts)
    add("updated_at", ts)
    add("valid_from", ts)
    return payload


async def _record_causality(
    conn: aiosqlite.Connection,
    fact_id: int,
    project: str,
    tenant_id: str,
    meta: dict[str, Any],
    parent_decision_id: int | None,
) -> None:
    """Record causal linkage for the fact."""
    from cortex.engine.flow.causality import (
        EDGE_DERIVED_FROM,
        EDGE_TRIGGERED_BY,
        EDGE_UPDATED_FROM,
        AsyncCausalGraph,
    )

    p_sig = meta.get("causal_parent")
    p_fact = meta.get("previous_fact_id")

    graph = AsyncCausalGraph(conn)

    if p_sig or p_fact:
        e_type = EDGE_UPDATED_FROM if p_fact else EDGE_TRIGGERED_BY
        await graph.record_edge(
            fact_id=fact_id,
            parent_id=p_fact,
            signal_id=p_sig,
            edge_type=e_type,
            project=project,
            tenant_id=tenant_id,
        )
    elif parent_decision_id:
        await graph.record_edge(
            fact_id=fact_id,
            parent_id=parent_decision_id,
            edge_type=EDGE_DERIVED_FROM,
            project=project,
            tenant_id=tenant_id,
        )


async def _post_insert_actions(
    conn: aiosqlite.Connection,
    fact_id: int,
    content: str,
    tenant_id: str,
    project: str,
    tags: list[str] | None,
    tags_json: str,
    fact_type: str,
    ts: str,
    meta: dict[str, Any],
    parent_decision_id: int | None,
) -> None:
    """Side effects: Enrichment jobs, Tags, FTS, Causality, and Graph."""
    try:
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, job_type, status, priority) VALUES (?, 'embedding', 'pending', ?)",
            (fact_id, 1 if fact_type == "decision" else 0),
        )
    except (OSError, ValueError, sqlite3.Error) as e:
        logger.error("Failed to insert enrichment job for fact %d: %s", fact_id, e)

    if tags:
        await conn.executemany(
            "INSERT OR IGNORE INTO fact_tags (fact_id, tag, tenant_id) VALUES (?, ?, ?)",
            [(fact_id, t, tenant_id) for t in tags],
        )

    try:
        await conn.execute(
            "INSERT OR REPLACE INTO facts_fts (rowid, content, project, tags, fact_type, tenant_id) VALUES (?, ?, ?, ?, ?, ?)",
            (fact_id, content, project, tags_json, fact_type, tenant_id),
        )
    except (OSError, ValueError, sqlite3.Error) as e:
        logger.error("Failed to insert FTS for fact %d: %s", fact_id, e)

    await _record_causality(conn, fact_id, project, tenant_id, meta, parent_decision_id)

    try:
        from cortex.graph import process_fact_graph

        await process_fact_graph(conn, fact_id, content, project, ts, tenant_id)
    except (ImportError, OSError, ValueError, sqlite3.Error) as e:
        logger.error("Failed to process graph for fact %d: %s", fact_id, e)


async def resolve_causality_async(
    conn: aiosqlite.Connection, project: str, meta: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve causal linking for a fact asynchronously.

    Ω₁: Every decision must point to its progenitor.
    """
    from cortex.engine.flow.causality import AsyncCausalOracle, link_causality

    if not (meta and meta.get("causal_parent")):
        parent_sig = await AsyncCausalOracle.find_parent_signal(conn, project)
        return link_causality(meta, parent_sig)
    return meta or {}


def resolve_causality(
    db_path: str | None, project: str, meta: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve causal linking for a fact (sync)."""
    from cortex.engine.flow.causality import CausalOracle, link_causality

    if db_path and not (meta and meta.get("causal_parent")):
        parent_sig = CausalOracle.find_parent_signal(db_path, project)
        return link_causality(meta, parent_sig)
    return meta or {}
