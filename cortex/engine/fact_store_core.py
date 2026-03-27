"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

# Hoisted from insert_fact_record hot path (was lazy import per-call)
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
    from cortex.extensions.security.signatures import get_default_signer
    from cortex.search.fts_index import plaintext_for_fts, replace_fact_fts_async

    ts = ts or now_iso()
    tags_json = json.dumps(tags or [])
    f_hash = compute_fact_hash(content)

    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)

    sig_b64: str | None = None
    pub_b64: str | None = None
    try:
        signer = get_default_signer()
        if signer and signer.can_sign:
            sig_b64 = signer.sign(content, f_hash)
            pub_b64 = signer.public_key_b64
    except (ImportError, ValueError, OSError) as e:
        logger.warning(
            "CORTEX-SECURITY: Fact signing skipped due to internal error. "
            "Audit visibility maintained. Error: %s",
            e,
        )

    meta = meta or {}

    canonical_tx_id = tx_id
    if canonical_tx_id is None:
        meta_tx_id = meta.get("tx_id")
        if isinstance(meta_tx_id, int):
            canonical_tx_id = meta_tx_id
        elif isinstance(meta_tx_id, str) and meta_tx_id.isdigit():
            canonical_tx_id = int(meta_tx_id)

    # ── Causal Infrastructure: Validate & Auto-Resolve parent_decision_id ──
    if parent_decision_id is not None:
        # FK validation — ensure parent exists within the SAME tenant scope
        async with conn.execute(
            "SELECT id FROM facts WHERE id = ? AND tenant_id = ?", (parent_decision_id, tenant_id)
        ) as cursor:
            if await cursor.fetchone() is None:
                logger.warning(
                    "parent_decision_id=%d references non-existent fact or "
                    "crosses tenant bounds — cleared",
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

    cognitive_layer = str(meta.get("cognitive_layer", "semantic") or "semantic")

    if sig_b64:
        meta["signature"] = sig_b64
    if pub_b64:
        meta["signer_pubkey"] = pub_b64

    encrypted_meta = enc.encrypt_json(meta, tenant_id=tenant_id)

    cursor = await conn.execute(
        "INSERT INTO facts (tenant_id, project, content, fact_type, tags, metadata, "
        "hash, created_at, updated_at, valid_from, confidence, source, tx_id, "
        "cognitive_layer, parent_decision_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tenant_id,
            project,
            encrypted_content,
            fact_type,
            tags_json,
            encrypted_meta,
            f_hash,
            ts,
            ts,
            ts,
            confidence,
            source,
            canonical_tx_id,
            cognitive_layer,
            parent_decision_id,
        ),
    )
    fact_id = cursor.lastrowid
    assert fact_id is not None

    # facts_fts is maintained manually. Encrypted rows are intentionally excluded.
    await replace_fact_fts_async(
        conn,
        fact_id,
        plaintext=plaintext_for_fts(content, encrypted_content),
        project=project,
        tags_json=tags_json,
        fact_type=fact_type,
    )

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

    except aiosqlite.Error as e:
        logger.debug("Database error during causal edge recording: %s", e)
    except Exception:
        logger.exception("Unexpected error during causal edge recording")

    return fact_id  # type: ignore[reportReturnType]
