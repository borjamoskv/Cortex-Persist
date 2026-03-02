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

    cursor = await conn.execute(
        "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence, "
        "valid_from, source, meta, hash, signature, signer_pubkey, "
        "created_at, updated_at, tx_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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

    # Graph Extraction
    from cortex.graph import process_fact_graph

    try:
        await process_fact_graph(conn, fact_id, content, project, ts)  # type: ignore[reportArgumentType]
    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
        logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

    return fact_id  # type: ignore[reportReturnType]


def resolve_causality(
    db_path: str | None, project: str, meta: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve causal linking for a fact."""
    from cortex.engine.causality import CausalOracle, link_causality

    if db_path and not (meta and meta.get("causal_parent")):
        parent_sig = CausalOracle.find_parent_signal(db_path, project)
        return link_causality(meta, parent_sig)
    return meta or {}
