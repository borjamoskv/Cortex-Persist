"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aiosqlite

from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex")

_FTS_SKIP_META_FLAGS = frozenset(
    {
        "contains_secret",
        "fts_disabled",
        "no_fts",
        "privacy_flagged",
        "requires_encryption_only",
        "sensitive",
    }
)
_FTS_PLAINTEXT_OPT_IN_META_FLAGS = frozenset(
    {
        "allow_plaintext_fts",
        "fts_plaintext",
        "searchable_plaintext",
    }
)


def _truthy_meta(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _should_index_plaintext_fts(meta: dict[str, Any]) -> bool:
    """Return whether plaintext content may be duplicated into the FTS side table."""
    explicitly_allowed = any(
        _truthy_meta(meta.get(flag)) for flag in _FTS_PLAINTEXT_OPT_IN_META_FLAGS
    )
    explicitly_denied = any(_truthy_meta(meta.get(flag)) for flag in _FTS_SKIP_META_FLAGS)
    return explicitly_allowed and not explicitly_denied


def _encrypt_fact_metadata(meta: dict[str, Any], tenant_id: str) -> str:
    """Encrypt non-empty fact metadata before at-rest persistence."""
    if not meta:
        return "{}"
    from cortex.crypto import get_default_encrypter

    encrypted = get_default_encrypter().encrypt_json(meta, tenant_id=tenant_id)
    if encrypted is None:
        return "{}"
    return encrypted


async def _get_table_columns(conn: aiosqlite.Connection, table_name: str) -> set[str]:
    """Return the set of column names for a SQLite table."""
    async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
        rows = await cursor.fetchall()
    return {str(row[1]) for row in rows}


async def _table_exists(conn: aiosqlite.Connection, table_name: str) -> bool:
    """Return whether a table or virtual table exists in the current schema."""
    async with conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')",
        (table_name,),
    ) as cursor:
        return await cursor.fetchone() is not None


async def _prepare_fact_content(
    content: str, tenant_id: str
) -> tuple[str, str, Optional[str], Optional[str]]:
    """Encrypted content and cryptographic signatures."""
    from cortex.crypto import get_default_encrypter
    from cortex.extensions.security.signatures import get_default_signer

    f_hash = compute_fact_hash(content)
    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
    if encrypted_content is None:
        raise ValueError("Encrypted fact content cannot be empty")

    sig_b64, pub_b64 = None, None
    try:
        signer = get_default_signer()
        if signer and signer.can_sign:
            sig_b64 = signer.sign(content, f_hash)
            pub_b64 = signer.public_key_b64
    except (ImportError, ValueError, OSError) as e:
        logger.debug("Fact signing skipped: %s", e)

    return f_hash, encrypted_content, sig_b64, pub_b64


async def _resolve_causal_parent(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    fact_type: str,
    parent_decision_id: Optional[int],
) -> Optional[int]:
    """Validate or auto-resolve the parent decision link."""
    if parent_decision_id is not None:
        async with conn.execute(
            "SELECT id FROM facts "
            "WHERE id = ? AND tenant_id = ? AND project = ? "
            "AND fact_type = 'decision' AND is_tombstoned = 0 "
            "AND valid_until IS NULL",
            (parent_decision_id, tenant_id, project),
        ) as cursor:
            if await cursor.fetchone() is None:
                raise ValueError(
                    "parent_decision_id is invalid, inactive, non-decision, "
                    "cross-project, or cross-tenant"
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
    tags: Optional[list[str]],
    confidence: str,
    ts: Optional[str],
    source: Optional[str],
    meta: Optional[dict[str, Any]],
    tx_id: Optional[int],
    parent_decision_id: Optional[int] = None,
) -> int:
    """Perform the actual SQL insert into the facts table."""
    ts = ts or now_iso()
    tags_json = json.dumps(tags or [])
    meta = dict(meta or {})

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
        meta,
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
        meta,
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
    source: Optional[str],
    confidence: str,
    parent_decision_id: Optional[int],
    tx_id: Optional[int],
    tags_json: str,
    ts: str,
) -> list[tuple[str, Any]]:
    """Construct the SQL payload with layout-aware column detection."""
    from cortex.engine.metadata_engine import MetadataEngine
    from cortex.engine.models import Fact

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

    meta_json = _encrypt_fact_metadata(meta, tenant_id)
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
    parent_decision_id: Optional[int],
) -> None:
    """Record causal linkage for the fact."""
    from cortex.engine.causality import EDGE_DERIVED_FROM, EDGE_TRIGGERED_BY, EDGE_UPDATED_FROM

    p_sig = meta.get("causal_parent")
    p_fact = _coerce_previous_fact_id(meta.get("previous_fact_id"))
    signal_id = _coerce_signal_id(p_sig)

    if p_fact is not None:
        await _validate_previous_fact(conn, p_fact, tenant_id, project)
    if signal_id is not None:
        await _validate_signal(conn, signal_id, tenant_id, project)

    if signal_id is not None or p_fact:
        e_type = EDGE_UPDATED_FROM if p_fact else EDGE_TRIGGERED_BY
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fact_id, p_fact, signal_id, e_type, project, tenant_id),
        )
    elif parent_decision_id:
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
            "VALUES (?, ?, NULL, ?, ?, ?)",
            (fact_id, parent_decision_id, EDGE_DERIVED_FROM, project, tenant_id),
        )


def _coerce_previous_fact_id(value: Any) -> int | None:
    """Normalize previous_fact_id metadata without accepting ambiguous values."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("previous_fact_id must be a positive integer")
    try:
        fact_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("previous_fact_id must be a positive integer") from exc
    if fact_id <= 0:
        raise ValueError("previous_fact_id must be a positive integer")
    return fact_id


def _coerce_signal_id(value: Any) -> int | None:
    """Normalize causal_parent signal IDs without accepting ambiguous values."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("causal_parent must be a positive integer signal id")
    try:
        signal_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("causal_parent must be a positive integer signal id") from exc
    if signal_id <= 0:
        raise ValueError("causal_parent must be a positive integer signal id")
    return signal_id


async def _validate_previous_fact(
    conn: aiosqlite.Connection,
    previous_fact_id: int,
    tenant_id: str,
    project: str,
) -> None:
    """Ensure metadata causal links cannot cross tenant or project boundaries.

    ``previous_fact_id`` is an audit/version edge, so the predecessor may already be
    deprecated or tombstoned by the write currently creating its successor.
    """
    async with conn.execute(
        "SELECT id FROM facts "
        "WHERE id = ? AND tenant_id = ? AND project = ?",
        (previous_fact_id, tenant_id, project),
    ) as cursor:
        if await cursor.fetchone() is None:
            raise ValueError("previous_fact_id is invalid, inactive, cross-project, or cross-tenant")


async def _validate_signal(
    conn: aiosqlite.Connection,
    signal_id: int,
    tenant_id: str,
    project: str,
) -> None:
    """Ensure signal causal links cannot cross tenant or project boundaries."""
    if not await _table_exists(conn, "signals"):
        raise ValueError("causal_parent signal_id is invalid or signals table is unavailable")
    signal_columns = await _get_table_columns(conn, "signals")
    if "tenant_id" not in signal_columns:
        raise RuntimeError("signals.tenant_id is required for causal signal validation")
    where = ["id = ?", "tenant_id = ?"]
    params: list[Any] = [signal_id, tenant_id]
    if "project" in signal_columns:
        where.append("(project = ? OR project IS NULL)")
        params.append(project)
    async with conn.execute(
        f"SELECT id FROM signals WHERE {' AND '.join(where)} LIMIT 1",
        params,
    ) as cursor:
        if await cursor.fetchone() is None:
            raise ValueError("causal_parent signal_id is invalid, cross-project, or cross-tenant")


async def _post_insert_actions(
    conn: aiosqlite.Connection,
    fact_id: int,
    content: str,
    tenant_id: str,
    project: str,
    tags: Optional[list[str]],
    tags_json: str,
    fact_type: str,
    ts: str,
    meta: dict[str, Any],
    parent_decision_id: Optional[int],
) -> None:
    """Side effects: Enrichment jobs, Tags, FTS, Causality, and Graph."""
    if await _table_exists(conn, "enrichment_jobs"):
        job_columns = await _get_table_columns(conn, "enrichment_jobs")
        if "tenant_id" in job_columns:
            await conn.execute(
                "INSERT INTO enrichment_jobs (tenant_id, fact_id, job_type, status, priority) "
                "VALUES (?, ?, 'embedding', 'pending', ?)",
                (tenant_id, fact_id, 1 if fact_type == "decision" else 0),
            )
        else:
            await conn.execute(
                "INSERT INTO enrichment_jobs (fact_id, job_type, status, priority) "
                "VALUES (?, 'embedding', 'pending', ?)",
                (fact_id, 1 if fact_type == "decision" else 0),
            )

    if tags:
        await conn.executemany(
            "INSERT OR IGNORE INTO fact_tags (fact_id, tag, tenant_id) VALUES (?, ?, ?)",
            [(fact_id, t, tenant_id) for t in tags],
        )

    if await _table_exists(conn, "facts_fts"):
        fts_columns = await _get_table_columns(conn, "facts_fts")
        if "tenant_id" not in fts_columns:
            raise RuntimeError("facts_fts must include tenant_id before indexing facts")
        if _should_index_plaintext_fts(meta):
            await conn.execute(
                "INSERT INTO facts_fts (rowid, content, project, tags, fact_type, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, content, project, tags_json, fact_type, tenant_id),
            )
        else:
            logger.info("Skipping plaintext FTS index for privacy-flagged fact %s", fact_id)

    await _record_causality(conn, fact_id, project, tenant_id, meta, parent_decision_id)

    try:
        from cortex.graph import process_fact_graph
    except ImportError:
        return

    await process_fact_graph(conn, fact_id, content, project, ts, tenant_id)


async def resolve_causality_async(
    conn: aiosqlite.Connection,
    project: str,
    meta: Optional[dict[str, Any]],
    tenant_id: str = "default",
) -> dict[str, Any]:
    """Resolve causal linking for a fact asynchronously.

    Ω₁: Every decision must point to its progenitor.
    """
    from cortex.engine.causality import AsyncCausalOracle, link_causality

    if not (meta and meta.get("causal_parent")):
        parent_sig = await AsyncCausalOracle.find_parent_signal(
            conn, tenant_id=tenant_id, project=project
        )
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
