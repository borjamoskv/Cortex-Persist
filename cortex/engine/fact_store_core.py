"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex")


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
) -> int:
    """Perform the actual SQL insert into the facts table."""
    from cortex.crypto import get_default_encrypter
    from cortex.security.signatures import get_default_signer

    ts = ts or now_iso()
    tags_json = json.dumps(tags or [])
    f_hash = compute_fact_hash(content)

    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
    encrypted_meta = enc.encrypt_json(meta, tenant_id=tenant_id)

    sig_b64: str | None = None
    pub_b64: str | None = None
    try:
        signer = get_default_signer()
        if signer and signer.can_sign:
            sig_b64 = signer.sign(content, f_hash)
            pub_b64 = signer.public_key_b64
    except (ImportError, ValueError, OSError) as e:
        logger.debug("Fact signing skipped: %s", e)

    # ── Causal Infrastructure: Validate & Auto-Resolve parent_decision_id ──
    if parent_decision_id is not None:
        # FK validation — ensure parent exists
        cursor = await conn.execute(
            "SELECT id FROM facts WHERE id = ?", (parent_decision_id,)
        )
        if await cursor.fetchone() is None:
            logger.warning(
                "parent_decision_id=%d references non-existent fact — cleared",
                parent_decision_id,
            )
            parent_decision_id = None
    elif fact_type in ("decision", "error"):
        # Auto-resolve: link to the most recent decision in the same project
        # Decisions chain to previous decisions; errors link to their cause.
        cursor = await conn.execute(
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ? "
            "AND fact_type = 'decision' AND is_tombstoned = 0 "
            "ORDER BY id DESC LIMIT 1",
            (project, tenant_id),
        )
        row = await cursor.fetchone()
        if row:
            parent_decision_id = row[0]
            logger.debug(
                "Auto-resolved parent_decision_id=%d for %s in project=%s",
                parent_decision_id, fact_type, project,
            )

    cursor = await conn.execute(
        "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence, "
        "valid_from, source, meta, hash, signature, signer_pubkey, "
        "created_at, updated_at, tx_id, parent_decision_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tenant_id,
            project,
            encrypted_content,
            fact_type,
            tags_json,
            confidence,
            ts,
            source,
            encrypted_meta,
            f_hash,
            sig_b64,
            pub_b64,
            ts,
            ts,
            tx_id,
            parent_decision_id,
        ),
    )
    fact_id = cursor.lastrowid

    # FTS Update
    try:
        await conn.execute(
            "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (fact_id, content, project, tags_json, fact_type),
        )
    except (sqlite3.Error, aiosqlite.Error) as e:
        logger.warning("Failed to update FTS for fact %d: %s", fact_id, e)

    # Causal Infrastructure (ANAMNESIS-Ω)
    try:
        from cortex.engine.causality import EDGE_TRIGGERED_BY, EDGE_UPDATED_FROM

        # Since causality.py schema uses sqlite3 directly in its record_edge (sync),
        # but we are in an async insert context, we'll perform the insert directly
        # here or via a future CausalGraph.record_edge_async call.
        # For now, we manually record to guarantee atomic async flow.

        # Ensure table exists (best effort, ideally initialized on startup)
        # Note: In production this should be handled by a migration or on startup.

        parent_signal = meta.get("causal_parent") if meta else None
        parent_fact = meta.get("previous_fact_id") if meta else None

        if parent_signal or parent_fact:
            edge_type = EDGE_UPDATED_FROM if parent_fact else EDGE_TRIGGERED_BY
            await conn.execute(
                "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fact_id,
                    parent_fact,
                    parent_signal,
                    edge_type,
                    project,
                    tenant_id,
                ),
            )
    except (ImportError, Exception) as e:  # noqa: BLE001
        logger.debug("Causal edge recording skipped for fact %d: %s", fact_id, e)

    # Graph Extraction
    from cortex.graph import process_fact_graph

    try:
        # type: ignore[reportArgumentType]
        await process_fact_graph(conn, fact_id, content, project, ts, tenant_id)
    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
        logger.warning("Graph extraction failed for fact %d (tenant=%s): %s", fact_id, tenant_id, e)

    return fact_id  # type: ignore[reportReturnType]


async def resolve_causality_async(
    conn: aiosqlite.Connection, project: str, meta: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve causal linking for a fact asynchronously.

    Ω₁: Every decision must point to its progenitor.
    """
    from cortex.engine.causality import AsyncCausalOracle, link_causality

    if not (meta and meta.get("causal_parent")):
        parent_sig = await AsyncCausalOracle.find_parent_signal(conn, project)
        return link_causality(meta, parent_sig)
    return meta or {}


def resolve_causality(
    db_path: str | None, project: str, meta: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve causal linking for a fact (sync)."""
    from cortex.engine.causality import CausalOracle, link_causality

    if db_path and not (meta and meta.get("causal_parent")):
        parent_sig = CausalOracle.find_parent_signal(db_path, project)
        return link_causality(meta, parent_sig)
    return meta or {}
