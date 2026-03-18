"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Optional

import aiosqlite

# Hoisted from insert_fact_record hot path (was lazy import per-call)
from cortex.graph import process_fact_graph
from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex")


async def insert_fact_record(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    content: str,
    fact_type: str,
    tags: Optional[list[str]],
    confidence: str,
    ts: Optional[str],
    source: Optional[str],
    meta: Optional[dict[str, Any]],
    tx_id: Optional[int],
    parent_decision_id: Optional[int] = None,
) -> int:
    """Perform the actual SQL insert into the facts table."""
    from cortex.crypto import get_default_encrypter
    from cortex.extensions.security.signatures import get_default_signer

    ts = ts or now_iso()
    tags_json = json.dumps(tags or [])
    f_hash = compute_fact_hash(content)

    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)

    sig_b64: Optional[str] = None
    pub_b64: Optional[str] = None
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
        async with conn.execute(
            "SELECT id FROM facts WHERE id = ?", (parent_decision_id,)
        ) as cursor:
            if await cursor.fetchone() is None:
                logger.warning(
                    "parent_decision_id=%d references non-existent fact — cleared",
                    parent_decision_id,
                )
                parent_decision_id = None
    elif fact_type in ("decision", "error"):
        # Auto-resolve: link to the most recent decision in the same project
        # Decisions chain to previous decisions; errors link to their cause.
        async with conn.execute(
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ? "
            "AND fact_type = 'decision' AND is_tombstoned = 0 "
            "ORDER BY id DESC LIMIT 1",
            (project, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            parent_decision_id = row[0]
            logger.debug(
                "Auto-resolved parent_decision_id=%d for %s in project=%s",
                parent_decision_id,
                fact_type,
                project,
            )

    # Re-pack legacy fields into meta JSON payload
    meta = meta or {}
    if confidence != "stated":
        meta["confidence"] = confidence
    if source:
        meta["source"] = source
    if parent_decision_id:
        meta["parent_decision_id"] = parent_decision_id
    if tx_id:
        meta["tx_id"] = tx_id
    if sig_b64:
        meta["signature"] = sig_b64
    if pub_b64:
        meta["signer_pubkey"] = pub_b64

    # encrypted_meta = enc.encrypt_json(meta, tenant_id=tenant_id)

    # ── Double-Plane Ingestion (V2) ──
    from cortex.engine.metadata_engine import MetadataEngine
    from cortex.engine.models import Fact
    
    # 1. Deterministic Classification (Heuristic-First)
    # We construct a temporary Fact object for classification
    temp_fact = Fact(
        id=0, # Placeholder
        tenant_id=tenant_id,
        project=project,
        content=content,
        fact_type=fact_type,
        tags=tags or [],
        parent_id=parent_decision_id,
        relation_type=meta.get("relation_type") if meta else None
    )
    metadata_v2 = MetadataEngine.classify_deterministic(temp_fact)
    
    category = metadata_v2["category"]
    quadrant = metadata_v2["quadrant"]
    storage_tier = metadata_v2["storage_tier"]
    exergy_score = metadata_v2["exergy_score"]
    yield_score = metadata_v2["yield_score"]
    relation_type = metadata_v2["relation_type"]

    # 2. SQL Persistence (facts table)
    async with conn.execute(
        """
        INSERT INTO facts (
            tenant_id, project, content, fact_type, metadata, hash, 
            source, confidence, parent_id, relation_type,
            quadrant, storage_tier, exergy_score, category, yield_score,
            semantic_status, tags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id, project, encrypted_content, fact_type, json.dumps(meta), f_hash,
            source, confidence, parent_decision_id, relation_type,
            quadrant, storage_tier, exergy_score, category, yield_score,
            "pending", tags_json
        ),
    ) as cursor:
        fact_id = cursor.lastrowid
    assert fact_id is not None

    # ── P0 Decoupling: Enqueue Enrichment Job ──
    try:
        await conn.execute(
            """
            INSERT INTO enrichment_jobs (fact_id, job_type, status, priority)
            VALUES (?, 'embedding', 'pending', ?)
            """,
            (fact_id, 1 if fact_type == "decision" else 0),
        )
    except (sqlite3.OperationalError, aiosqlite.Error) as e:
        # If the table doesn't exist yet (e.g. migration hasn't run), create it
        if "no such table: enrichment_jobs" in str(e).lower():
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS enrichment_jobs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_id         INTEGER NOT NULL REFERENCES facts(id),
                    job_type        TEXT NOT NULL DEFAULT 'embedding',
                    status          TEXT NOT NULL DEFAULT 'pending',
                    priority        INTEGER DEFAULT 0,
                    attempts        INTEGER DEFAULT 0,
                    last_error      TEXT,
                    payload         TEXT,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await conn.execute(
                "INSERT INTO enrichment_jobs (fact_id, job_type, status, priority) VALUES (?, 'embedding', 'pending', ?)",
                (fact_id, 1 if fact_type == "decision" else 0),
            )
        else:
            logger.warning("Failed to enqueue enrichment job for fact %d: %s", fact_id, e)

    # 3. Tag Persistence (fact_tags bridge table)
    if tags:
        tag_records = [(fact_id, tag, tenant_id) for tag in tags]
        await conn.executemany(
            "INSERT OR IGNORE INTO fact_tags (fact_id, tag, tenant_id) VALUES (?, ?, ?)",
            tag_records
        )

    # 4. FTS Update (facts_fts virtual table)
    try:
        # We mirror a subset to FTS for fast keyword search
        await conn.execute(
            "INSERT INTO facts_fts (rowid, content, project, tags, fact_type) VALUES (?, ?, ?, ?, ?)",
            (fact_id, content, project, tags_json, fact_type)
        )
    except (sqlite3.Error, aiosqlite.Error) as e:
        if "unique" in str(e).lower() or "constraint failed" in str(e).lower():
            logger.debug("FTS entry already exists for fact %d (likely via trigger)", fact_id)
        else:
            logger.warning("FTS insert failed for fact %d: %s", fact_id, e)

    # Causal Infrastructure (ANAMNESIS-Ω)
    try:
        from cortex.engine.causality import (
            EDGE_DERIVED_FROM,
            EDGE_TRIGGERED_BY,
            EDGE_UPDATED_FROM,
        )

        parent_signal = meta.get("causal_parent") if meta else None
        parent_fact = meta.get("previous_fact_id") if meta else None

        edge_recorded = False
        if parent_signal or parent_fact:
            edge_type = EDGE_UPDATED_FROM if parent_fact else EDGE_TRIGGERED_BY
            await conn.execute(
                "INSERT INTO causal_edges "
                "(fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, parent_fact, parent_signal, edge_type, project, tenant_id),
            )
            edge_recorded = True

        # Ω₁₁ Densification: wire auto-resolved parent_decision_id → causal_edges
        if not edge_recorded and parent_decision_id:
            await conn.execute(
                "INSERT INTO causal_edges "
                "(fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                "VALUES (?, ?, NULL, ?, ?, ?)",
                (fact_id, parent_decision_id, EDGE_DERIVED_FROM, project, tenant_id),
            )

    except (ImportError, Exception) as e:  # noqa: BLE001
        logger.debug("Causal edge recording skipped for fact %d: %s", fact_id, e)

    # Graph Extraction
    try:
        # type: ignore[reportArgumentType]
        await process_fact_graph(conn, fact_id, content, project, ts, tenant_id)
    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
        logger.warning("Graph extraction failed for fact %d (tenant=%s): %s", fact_id, tenant_id, e)

    return fact_id  # type: ignore[reportReturnType]


async def resolve_causality_async(
    conn: aiosqlite.Connection, project: str, meta: Optional[dict[str, Any]]
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
    db_path: Optional[str], project: str, meta: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """Resolve causal linking for a fact (sync)."""
    from cortex.engine.causality import CausalOracle, link_causality

    if db_path and not (meta and meta.get("causal_parent")):
        parent_sig = CausalOracle.find_parent_signal(db_path, project)
        return link_causality(meta, parent_sig)
    return meta or {}
