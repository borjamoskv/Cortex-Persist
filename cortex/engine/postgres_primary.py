"""Primary PostgreSQL engine path for the public API vertical slice.

This adapter gives the main API a real store -> ledger -> query flow on
PostgreSQL/AlloyDB while delegating unsupported features to the legacy engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from cortex.consensus.merkle import MerkleTree as VoteMerkleTree
from cortex.crypto import get_default_encrypter
from cortex.engine.store_validators import validate_content
from cortex.ledger.sovereign_ledger import MerkleTree as SovereignMerkleTree
from cortex.memory.temporal import now_iso
from cortex.search.models import SearchResult
from cortex.utils.canonical import canonical_json, compute_fact_hash, compute_tx_hash

__all__ = ["PostgresPrimaryEngine"]

logger = logging.getLogger("cortex.engine.postgres_primary")

_FACT_SELECT = """
SELECT
    id,
    tenant_id,
    project,
    content,
    fact_type,
    tags,
    confidence,
    valid_from,
    valid_until,
    source,
    meta,
    consensus_score,
    hash,
    is_quarantined,
    quarantined_at,
    quarantine_reason,
    created_at,
    updated_at,
    tx_id,
    is_tombstoned,
    tombstoned_at
FROM facts
"""


def _postgres_vector_error_types() -> tuple[type[BaseException], ...]:
    """Return SQL error types that should trigger vector-search fallback."""
    try:
        import asyncpg
    except ImportError:
        return (RuntimeError, TypeError, ValueError)
    return (RuntimeError, TypeError, ValueError, asyncpg.PostgresError)


_POSTGRES_VECTOR_ERRORS = _postgres_vector_error_types()
_VOTE_LEDGER_GENESIS_HASH = "0" * 64
_VOTE_MERKLE_BATCH_SIZE = 1000


class PostgresPrimaryEngine:
    """Minimal primary engine backed by PostgreSQL for public API paths."""

    def __init__(self, backend: Any, fallback_engine: Any = None, embedder: Any = None):
        self._backend = backend
        self._fallback = fallback_engine
        self._embedder = embedder

    def _resolve_tenant(self, tenant_id: str) -> str:
        if tenant_id == "default":
            from cortex.extensions.security.tenant import get_tenant_id

            tenant_id = get_tenant_id()
        return tenant_id or "default"

    async def store(
        self,
        project: str,
        content: str,
        tenant_id: str = "default",
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        valid_from: str | None = None,
        parent_decision_id: int | None = None,
        **_: Any,
    ) -> int:
        """Store a fact directly into PostgreSQL with an atomic ledger write."""
        tenant_id = self._resolve_tenant(tenant_id)
        content = validate_content(project, content, fact_type)
        tags_json = json.dumps(tags or [])
        fact_hash = compute_fact_hash(content)
        existing = await self._backend.execute(
            "SELECT id FROM facts "
            "WHERE tenant_id = ? AND project = ? AND hash = ? "
            "AND is_tombstoned = FALSE AND is_quarantined = FALSE AND valid_until IS NULL "
            "LIMIT 1",
            (tenant_id, project, fact_hash),
        )
        if existing:
            return int(existing[0]["id"])

        ts = valid_from or now_iso()
        enc = get_default_encrypter()
        encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
        if encrypted_content is None:
            raise RuntimeError("Encryption returned no ciphertext for PostgreSQL primary store()")
        embedding = await self._embed_text(content)

        fact_meta = dict(meta or {})
        if source:
            fact_meta.setdefault("source", source)
        if confidence != "stated":
            fact_meta.setdefault("confidence", confidence)
        if parent_decision_id is not None:
            fact_meta["parent_decision_id"] = parent_decision_id

        async with self._backend.connection() as conn:
            async with conn.transaction():
                # Establecer tenant en el contexto para RLS (Row-Level Security)
                await self._backend.execute_with_conn(
                    conn, "SELECT set_config('cortex.tenant_id', ?, true)", (tenant_id,)
                )
                tx_id = await self._log_transaction(
                    conn,
                    project=project,
                    action="store",
                    detail={"fact_type": fact_type},
                    tenant_id=tenant_id,
                )
                fact_meta.setdefault("tx_id", tx_id)
                encrypted_meta = enc.encrypt_json(fact_meta, tenant_id=tenant_id)
                meta_payload = json.dumps(encrypted_meta) if encrypted_meta is not None else "{}"
                fact_id = await self._insert_fact(
                    conn,
                    tenant_id=tenant_id,
                    project=project,
                    encrypted_content=encrypted_content,
                    fact_type=fact_type,
                    tags_json=tags_json,
                    confidence=confidence,
                    timestamp=ts,
                    source=source,
                    meta_payload=meta_payload,
                    fact_hash=fact_hash,
                    tx_id=tx_id,
                    embedding=embedding,
                )

        return fact_id

    async def _insert_fact(
        self,
        conn: Any,
        *,
        tenant_id: str,
        project: str,
        encrypted_content: str,
        fact_type: str,
        tags_json: str,
        confidence: str,
        timestamp: str,
        source: str | None,
        meta_payload: str,
        fact_hash: str,
        tx_id: int,
        embedding: list[float] | None,
    ) -> int:
        base_params = (
            tenant_id,
            project,
            encrypted_content,
            fact_type,
            tags_json,
            confidence,
            timestamp,
            None,
            source,
            meta_payload,
            1.0,
            fact_hash,
            timestamp,
            timestamp,
            tx_id,
        )
        if embedding is not None:
            try:
                async with conn.transaction():
                    return await self._backend.execute_insert_with_conn(
                        conn,
                        "INSERT INTO facts "
                        "("
                        "tenant_id, project, content, fact_type, tags, confidence, "
                        "valid_from, valid_until, source, meta, consensus_score, hash, "
                        "created_at, updated_at, tx_id, embedding, is_tombstoned, is_quarantined"
                        ") VALUES ("
                        "?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?::vector, FALSE, FALSE"
                        ")",
                        (*base_params, self._vector_literal(embedding)),
                    )
            except _POSTGRES_VECTOR_ERRORS as exc:
                logger.warning(
                    "PostgreSQL vector insert unavailable, storing fact without embedding: %s", exc
                )

        return await self._backend.execute_insert_with_conn(
            conn,
            "INSERT INTO facts "
            "("
            "tenant_id, project, content, fact_type, tags, confidence, "
            "valid_from, valid_until, source, meta, consensus_score, hash, "
            "created_at, updated_at, tx_id, is_tombstoned, is_quarantined"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, FALSE, FALSE)",
            base_params,
        )

    async def _log_transaction(
        self,
        conn: Any,
        *,
        project: str,
        action: str,
        detail: dict[str, Any],
        tenant_id: str,
    ) -> int:
        detail_json = canonical_json(detail)
        ts = now_iso()
        prev = await self._backend.fetchrow_with_conn(
            conn,
            "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        prev_hash = str(prev["hash"]) if prev is not None else "GENESIS"
        tx_hash = compute_tx_hash(prev_hash, project, action, detail_json, ts)
        return await self._backend.execute_insert_with_conn(
            conn,
            "INSERT INTO transactions "
            "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tenant_id, project, action, detail_json, prev_hash, tx_hash, ts),
        )

    async def recall(
        self,
        project: str,
        limit: int | None = None,
        tenant_id: str = "default",
        fact_type: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Recall active facts directly from PostgreSQL."""
        tenant_id = self._resolve_tenant(tenant_id)
        sql = (
            f"{_FACT_SELECT} "
            "WHERE tenant_id = ? AND project = ? "
            "AND is_tombstoned = FALSE AND is_quarantined = FALSE"
        )
        params: list[Any] = [tenant_id, project]
        if fact_type:
            sql += " AND fact_type = ?"
            params.append(fact_type)
        sql += " ORDER BY created_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset:
            sql += " OFFSET ?"
            params.append(offset)
        rows = await self._backend.execute(sql, tuple(params))
        return [self._row_to_fact(row) for row in rows]

    async def get_fact(self, fact_id: int, tenant_id: str = "default") -> dict[str, Any] | None:
        """Get a fact by ID from PostgreSQL."""
        tenant_id = self._resolve_tenant(tenant_id)
        rows = await self._backend.execute(
            f"{_FACT_SELECT} WHERE tenant_id = ? AND id = ? LIMIT 1",
            (tenant_id, fact_id),
        )
        if not rows:
            return None
        return self._row_to_fact(rows[0])

    async def delete(self, fact_id: int, tenant_id: str = "default") -> None:
        """Hard delete a fact from PostgreSQL with ledger tracing."""
        tenant_id = self._resolve_tenant(tenant_id)
        async with self._backend.connection() as conn:
            async with conn.transaction():
                # Establecer tenant para RLS
                await self._backend.execute_with_conn(
                    conn, "SELECT set_config('cortex.tenant_id', ?, true)", (tenant_id,)
                )
                _ = await self._log_transaction(
                    conn,
                    project="cortex-core",
                    action="delete",
                    detail={"fact_id": fact_id},
                    tenant_id=tenant_id,
                )
                await self._backend.execute_with_conn(
                    conn,
                    "DELETE FROM facts WHERE id = ? AND tenant_id = ?",
                    (fact_id, tenant_id)
                )

    async def tombstone(self, fact_id: int, tenant_id: str = "default") -> None:
        """Soft delete (tombstone) a fact from PostgreSQL."""
        tenant_id = self._resolve_tenant(tenant_id)
        async with self._backend.connection() as conn:
            async with conn.transaction():
                # Establecer tenant para RLS
                await self._backend.execute_with_conn(
                    conn, "SELECT set_config('cortex.tenant_id', ?, true)", (tenant_id,)
                )
                _ = await self._log_transaction(
                    conn,
                    project="cortex-core",
                    action="tombstone",
                    detail={"fact_id": fact_id},
                    tenant_id=tenant_id,
                )
                await self._backend.execute_with_conn(
                    conn,
                    "UPDATE facts SET is_tombstoned = TRUE, tombstoned_at = ?, updated_at = ? WHERE id = ? AND tenant_id = ?",
                    (now_iso(), now_iso(), fact_id, tenant_id)
                )

    async def vote(
        self,
        fact_id: int,
        agent: str,
        value: int,
        signature: str | None = None,
        **_: Any,
    ) -> float:
        """Cast a vote directly against PostgreSQL with immutable vote-ledger logging."""
        if value not in (-1, 0, 1):
            raise ValueError("Vote must be -1, 0, or 1")

        async with self._backend.connection() as conn:
            async with conn.transaction():
                fact_row = await self._backend.fetchrow_with_conn(
                    conn,
                    "SELECT id, tenant_id, project FROM facts WHERE id = ? LIMIT 1",
                    (fact_id,),
                )
                if fact_row is None:
                    raise ValueError(f"Fact #{fact_id} not found")

                # Establecer tenant para RLS
                await self._backend.execute_with_conn(
                    conn, "SELECT set_config('cortex.tenant_id', ?, true)", (str(fact_row.get("tenant_id") or "default"),)
                )

                tenant_id = self._resolve_tenant(str(fact_row.get("tenant_id") or "default"))
                project = str(fact_row["project"])
                vote_weight = await self._resolve_agent_rep(conn, agent, tenant_id)
                tx_id = await self._log_transaction(
                    conn,
                    project=project,
                    action="vote_v2",
                    detail={"fact_id": fact_id, "agent_id": agent, "vote": value},
                    tenant_id=tenant_id,
                )
                await self._store_consensus_vote(
                    conn,
                    fact_id=fact_id,
                    agent_id=agent,
                    value=value,
                    vote_weight=vote_weight,
                    tx_id=tx_id,
                    signature=signature,
                )
                await self._append_vote_ledger_entry(
                    conn,
                    tenant_id=tenant_id,
                    fact_id=fact_id,
                    agent_id=agent,
                    value=value,
                    vote_weight=vote_weight,
                    tx_id=tx_id,
                    signature=signature,
                )
                score = await self._update_vote_score(conn, fact_id, tenant_id)
                confidence = self._resolve_confidence(score)
                await self._backend.execute_with_conn(
                    conn,
                    "UPDATE facts "
                    "SET consensus_score = ?, confidence = ?, updated_at = ? "
                    "WHERE id = ? AND tenant_id = ?",
                    (score, confidence, now_iso(), fact_id, tenant_id),
                )
                await self._maybe_create_vote_checkpoint(conn, tenant_id)
                return score

    async def get_votes(self, fact_id: int) -> list[tuple[str, int, int | None]]:
        """List canonical votes for a fact from PostgreSQL."""
        rows = await self._backend.execute(
            "SELECT agent_id, vote, tx_id FROM consensus_votes_v2 WHERE fact_id = ? ORDER BY id",
            (fact_id,),
        )
        return [
            (str(row["agent_id"]), int(row["vote"]), self._optional_int(row.get("tx_id")))
            for row in rows
        ]

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: int = 5,
        project: str | None = None,
        **_: Any,
    ) -> list[SearchResult]:
        """Search PostgreSQL facts using pgvector when available, with safe fallback."""
        tenant_id = self._resolve_tenant(tenant_id)
        query_embedding = await self._embed_text(query)
        vector_results: list[SearchResult] = []
        if query_embedding is not None:
            try:
                vector_results = await self._search_by_vector(
                    query=query,
                    tenant_id=tenant_id,
                    top_k=top_k,
                    project=project,
                    query_embedding=query_embedding,
                )
            except _POSTGRES_VECTOR_ERRORS as exc:
                logger.warning(
                    "PostgreSQL vector search unavailable, falling back to scan: %s", exc
                )

        if len(vector_results) >= top_k:
            return vector_results[:top_k]

        scan_results = await self._search_by_scan(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
            project=project,
        )
        if not vector_results:
            return scan_results[:top_k]

        seen = {result.fact_id for result in vector_results}
        merged = list(vector_results)
        for result in scan_results:
            if result.fact_id in seen:
                continue
            merged.append(result)
            seen.add(result.fact_id)
            if len(merged) >= top_k:
                break
        return merged[:top_k]

    async def _search_by_vector(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int,
        project: str | None,
        query_embedding: list[float],
    ) -> list[SearchResult]:
        query_literal = self._vector_literal(query_embedding)
        sql = (
            "SELECT "
            "id, tenant_id, project, content, fact_type, tags, confidence, "
            "valid_from, valid_until, source, meta, consensus_score, hash, "
            "is_quarantined, quarantined_at, quarantine_reason, created_at, updated_at, "
            "tx_id, is_tombstoned, tombstoned_at, "
            "(1 - (embedding <=> ?::vector)) AS score "
            "FROM facts "
            "WHERE tenant_id = ? AND is_tombstoned = FALSE AND is_quarantined = FALSE "
            "AND embedding IS NOT NULL"
        )
        params: list[Any] = [query_literal, tenant_id]
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY embedding <=> ?::vector ASC LIMIT ?"
        params.extend((query_literal, top_k))

        rows = await self._backend.execute(sql, tuple(params))
        results: list[SearchResult] = []
        for row in rows:
            fact = self._row_to_fact(row)
            score = max(0.0, min(1.0, float(row.get("score") or 0.0)))
            results.append(self._fact_to_search_result(fact, score))
        return results

    async def _search_by_scan(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int,
        project: str | None,
    ) -> list[SearchResult]:
        sql = (
            f"{_FACT_SELECT} "
            "WHERE tenant_id = ? AND is_tombstoned = FALSE AND is_quarantined = FALSE"
        )
        params: list[Any] = [tenant_id]
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(50, top_k * 20))

        rows = await self._backend.execute(sql, tuple(params))
        facts = [self._row_to_fact(row) for row in rows]

        results: list[SearchResult] = []
        for fact in facts:
            score = self._score_query(query, fact)
            if score <= 0:
                continue
            results.append(self._fact_to_search_result(fact, score))

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _score_query(self, query: str, fact: dict[str, Any]) -> float:
        query_norm = query.strip().casefold()
        if not query_norm:
            return 0.0

        haystack = " ".join(
            [
                str(fact.get("content") or ""),
                " ".join(str(tag) for tag in fact.get("tags") or []),
                str(fact.get("source") or ""),
            ]
        ).casefold()

        if query_norm in haystack:
            return 1.0

        tokens = [token for token in query_norm.split() if token]
        if tokens:
            token_hits = sum(1 for token in tokens if token in haystack)
            if token_hits:
                return token_hits / len(tokens)

        ratio = SequenceMatcher(a=query_norm, b=haystack[: max(len(query_norm) * 6, 1)]).ratio()
        return ratio if ratio >= 0.35 else 0.0

    def _fact_to_search_result(self, fact: dict[str, Any], score: float) -> SearchResult:
        return SearchResult(
            fact_id=int(fact["id"]),
            content=str(fact["content"]),
            project=str(fact["project"]),
            fact_type=str(fact["fact_type"]),
            confidence=str(fact["confidence"]),
            valid_from=str(fact["valid_from"]),
            valid_until=fact["valid_until"],
            tags=list(fact["tags"]),
            created_at=str(fact["created_at"]),
            updated_at=str(fact["updated_at"]),
            score=score,
            source=fact.get("source"),
            meta=fact.get("meta") or {},
            tx_id=fact.get("tx_id"),
            hash=fact.get("hash"),
            db_origin="postgres",
        )

    async def _resolve_agent_rep(self, conn: Any, agent_id: str, tenant_id: str) -> float:
        row = await self._backend.fetchrow_with_conn(
            conn,
            "SELECT reputation_score FROM agents WHERE id = ? AND tenant_id = ? LIMIT 1",
            (agent_id, tenant_id),
        )
        if row is not None:
            return float(row["reputation_score"])

        is_human = agent_id == "human"
        initial_rep = 1.0 if is_human else 0.5
        await self._backend.execute_with_conn(
            conn,
            "INSERT INTO agents "
            "(id, public_key, name, agent_type, tenant_id, reputation_score) "
            "VALUES (?, '', ?, ?, ?, ?) "
            "ON CONFLICT (id) DO NOTHING",
            (
                agent_id,
                agent_id.capitalize(),
                "human" if is_human else "ai",
                tenant_id,
                initial_rep,
            ),
        )
        return initial_rep

    async def _store_consensus_vote(
        self,
        conn: Any,
        *,
        fact_id: int,
        agent_id: str,
        value: int,
        vote_weight: float,
        tx_id: int,
        signature: str | None,
    ) -> None:
        if value == 0:
            await self._backend.execute_with_conn(
                conn,
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent_id),
            )
            return

        ts = now_iso()
        vote_meta = {"signature": signature} if signature else {}
        vote_reason = "api vote"
        params_with_tx = (
            fact_id,
            agent_id,
            value,
            vote_weight,
            vote_weight,
            0.0,
            ts,
            1.0,
            vote_reason,
            json.dumps(vote_meta),
            tx_id,
        )
        try:
            await self._backend.execute_insert_with_conn(
                conn,
                "INSERT INTO consensus_votes_v2 "
                "("
                "fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, stake_at_vote, "
                "created_at, decay_factor, vote_reason, meta, tx_id"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?) "
                "ON CONFLICT (fact_id, agent_id) DO UPDATE SET "
                "vote = EXCLUDED.vote, "
                "vote_weight = EXCLUDED.vote_weight, "
                "agent_rep_at_vote = EXCLUDED.agent_rep_at_vote, "
                "stake_at_vote = EXCLUDED.stake_at_vote, "
                "created_at = EXCLUDED.created_at, "
                "decay_factor = EXCLUDED.decay_factor, "
                "vote_reason = EXCLUDED.vote_reason, "
                "meta = EXCLUDED.meta, "
                "tx_id = EXCLUDED.tx_id",
                params_with_tx,
            )
        except _POSTGRES_VECTOR_ERRORS as exc:
            logger.warning(
                "consensus_votes_v2.tx_id unavailable, falling back without tx_id: %s", exc
            )
            await self._backend.execute_insert_with_conn(
                conn,
                "INSERT INTO consensus_votes_v2 "
                "("
                "fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, stake_at_vote, "
                "created_at, decay_factor, vote_reason, meta"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb) "
                "ON CONFLICT (fact_id, agent_id) DO UPDATE SET "
                "vote = EXCLUDED.vote, "
                "vote_weight = EXCLUDED.vote_weight, "
                "agent_rep_at_vote = EXCLUDED.agent_rep_at_vote, "
                "stake_at_vote = EXCLUDED.stake_at_vote, "
                "created_at = EXCLUDED.created_at, "
                "decay_factor = EXCLUDED.decay_factor, "
                "vote_reason = EXCLUDED.vote_reason, "
                "meta = EXCLUDED.meta",
                params_with_tx[:-1],
            )

    async def _append_vote_ledger_entry(
        self,
        conn: Any,
        *,
        tenant_id: str,
        fact_id: int,
        agent_id: str,
        value: int,
        vote_weight: float,
        tx_id: int,
        signature: str | None,
    ) -> int:
        prev = await self._backend.fetchrow_with_conn(
            conn,
            "SELECT hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        prev_hash = str(prev["hash"]) if prev is not None else _VOTE_LEDGER_GENESIS_HASH
        ts = now_iso()
        entry_hash = self._compute_vote_hash(prev_hash, fact_id, agent_id, value, vote_weight, ts)
        return await self._backend.execute_insert_with_conn(
            conn,
            "INSERT INTO vote_ledger "
            "(tenant_id, fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp, "
            "signature, tx_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                fact_id,
                agent_id,
                value,
                vote_weight,
                prev_hash,
                entry_hash,
                ts,
                signature,
                tx_id,
            ),
        )

    async def _update_vote_score(self, conn: Any, fact_id: int, tenant_id: str) -> float:
        rows = await self._backend.fetch_with_conn(
            conn,
            "SELECT v.vote, v.vote_weight, a.reputation_score "
            "FROM consensus_votes_v2 v "
            "JOIN agents a ON v.agent_id = a.id "
            "WHERE v.fact_id = ? AND a.is_active = TRUE AND a.tenant_id = ?",
            (fact_id, tenant_id),
        )
        if not rows:
            return 1.0

        weighted_sum = 0.0
        total_weight = 0.0
        for row in rows:
            vote_value = int(row["vote"])
            effective_weight = max(float(row["vote_weight"]), float(row["reputation_score"]))
            weighted_sum += vote_value * effective_weight
            total_weight += effective_weight
        return 1.0 + (weighted_sum / total_weight) if total_weight > 0 else 1.0

    async def _maybe_create_vote_checkpoint(self, conn: Any, tenant_id: str) -> int | None:
        rows = await self._backend.fetch_with_conn(
            conn,
            "SELECT id FROM vote_ledger "
            "WHERE tenant_id = ? "
            "AND id > COALESCE(("
            "SELECT MAX(vote_end_id) FROM vote_merkle_roots WHERE tenant_id = ?"
            "), 0) "
            "ORDER BY id",
            (tenant_id, tenant_id),
        )
        if len(rows) < _VOTE_MERKLE_BATCH_SIZE:
            return None
        return await self._create_vote_checkpoint_with_conn(
            conn, tenant_id, rows[:_VOTE_MERKLE_BATCH_SIZE]
        )

    async def create_vote_checkpoint(self, tenant_id: str = "default") -> int | None:
        """Create a Merkle checkpoint for pending immutable vote-ledger entries."""
        tenant_id = self._resolve_tenant(tenant_id)
        async with self._backend.connection() as conn:
            async with conn.transaction():
                rows = await self._backend.fetch_with_conn(
                    conn,
                    "SELECT id, hash FROM vote_ledger "
                    "WHERE tenant_id = ? "
                    "AND id > COALESCE(("
                    "SELECT MAX(vote_end_id) FROM vote_merkle_roots WHERE tenant_id = ?"
                    "), 0) "
                    "ORDER BY id LIMIT ?",
                    (tenant_id, tenant_id, _VOTE_MERKLE_BATCH_SIZE),
                )
                if not rows:
                    return None
                return await self._create_vote_checkpoint_with_conn(conn, tenant_id, rows)

    async def _create_vote_checkpoint_with_conn(
        self,
        conn: Any,
        tenant_id: str,
        rows: list[dict[str, Any]],
    ) -> int:
        hashes = [str(row["hash"]) for row in rows]
        start_id = int(rows[0]["id"])
        end_id = int(rows[-1]["id"])
        root_hash = VoteMerkleTree(hashes).root
        return await self._backend.execute_insert_with_conn(
            conn,
            "INSERT INTO vote_merkle_roots "
            "(tenant_id, root_hash, vote_start_id, vote_end_id, vote_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (tenant_id, root_hash, start_id, end_id, len(rows)),
        )

    @staticmethod
    def _resolve_confidence(score: float) -> str:
        if score >= 1.5:
            return "verified"
        if score <= 0.5:
            return "disputed"
        return "stated"

    @staticmethod
    def _compute_vote_hash(
        prev_hash: str,
        fact_id: int,
        agent_id: str,
        value: int,
        vote_weight: float | Decimal,
        timestamp: str,
    ) -> str:
        """Deterministically compute vote hash. Matches ImmutableVoteLedger parity."""
        weight_dec = Decimal(str(vote_weight))
        payload = f"{prev_hash}:{fact_id}:{agent_id}:{value}:{weight_dec}:{timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_embedder(self) -> Any:
        if self._embedder is None:
            from cortex.embeddings.manager import EmbeddingManager

            self._embedder = EmbeddingManager(self)
        return self._embedder

    async def _embed_text(self, text: str) -> list[float] | None:
        if not text.strip():
            return None
        try:
            raw_embedding = await asyncio.to_thread(self._get_embedder().embed, text)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("Embedding unavailable for PostgreSQL primary path: %s", exc)
            return None
        if not isinstance(raw_embedding, list) or not raw_embedding:
            return None
        if isinstance(raw_embedding[0], list):
            return None
        try:
            return [float(value) for value in raw_embedding]
        except (TypeError, ValueError):
            return None

    async def bootstrap_rls(self) -> None:
        """Apply Row-Level Security (RLS) policies to PostgreSQL schema."""
        logger.info("Bootstrapping Row-Level Security (RLS) policies...")
        policies = [
            "ALTER TABLE facts ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE vote_ledger ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY tenant_isolation_facts ON facts USING (tenant_id = current_setting('cortex.tenant_id', true));",
            "CREATE POLICY tenant_isolation_txs ON transactions USING (tenant_id = current_setting('cortex.tenant_id', true));",
            "CREATE POLICY tenant_isolation_votes ON vote_ledger USING (tenant_id = current_setting('cortex.tenant_id', true));",
        ]
        async with self._backend.connection() as conn:
            for sql in policies:
                try:
                    await self._backend.execute_with_conn(conn, sql, ())
                except _POSTGRES_VECTOR_ERRORS as exc:
                    logger.debug("RLS Policy exist or error: %s", exc)


    def _vector_literal(self, embedding: list[float]) -> str:
        return json.dumps([float(value) for value in embedding], separators=(",", ":"))

    def _row_to_fact(self, row: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(row.get("tenant_id") or "default")
        enc = get_default_encrypter()

        raw_content = row.get("content")
        try:
            content = enc.decrypt_str(raw_content, tenant_id=tenant_id) if raw_content else ""
        except (RuntimeError, ValueError, TypeError):
            content = f"[ENCRYPTED — decryption failed] (fact #{row.get('id')})"

        tags = self._decode_tags(row.get("tags"))
        meta = self._decode_meta(row.get("meta"), tenant_id)

        return {
            "id": int(row["id"]),
            "tenant_id": tenant_id,
            "project": str(row["project"]),
            "content": content,
            "fact_type": str(row["fact_type"]),
            "type": str(row["fact_type"]),
            "tags": tags,
            "confidence": str(row.get("confidence") or meta.get("confidence") or "stated"),
            "valid_from": row.get("valid_from") or row.get("created_at"),
            "valid_until": row.get("valid_until"),
            "source": row.get("source") or meta.get("source"),
            "meta": meta,
            "consensus_score": float(row.get("consensus_score") or 1.0),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "tx_id": row.get("tx_id") or meta.get("tx_id"),
            "hash": row.get("hash"),
            "is_quarantined": bool(row.get("is_quarantined")),
            "is_tombstoned": bool(row.get("is_tombstoned")),
            "parent_decision_id": meta.get("parent_decision_id"),
        }

    def _decode_tags(self, raw_tags: Any) -> list[str]:
        if isinstance(raw_tags, list):
            return [str(tag) for tag in raw_tags]
        if isinstance(raw_tags, str):
            try:
                decoded = json.loads(raw_tags)
            except json.JSONDecodeError:
                return []
            if isinstance(decoded, list):
                return [str(tag) for tag in decoded]
        return []

    def _decode_meta(self, raw_meta: Any, tenant_id: str) -> dict[str, Any]:
        if raw_meta is None:
            return {}
        if isinstance(raw_meta, dict):
            return raw_meta

        enc = get_default_encrypter()
        if isinstance(raw_meta, str):
            decrypted = self._decrypt_meta_str(raw_meta, tenant_id, enc)
            if decrypted is not None:
                return decrypted
            try:
                decoded = json.loads(raw_meta)
            except json.JSONDecodeError:
                return {}
            if isinstance(decoded, dict):
                return decoded
            if isinstance(decoded, str):
                decrypted = self._decrypt_meta_str(decoded, tenant_id, enc)
                return decrypted or {}

        return {}

    def _decrypt_meta_str(
        self,
        value: str,
        tenant_id: str,
        enc: Any,
    ) -> dict[str, Any] | None:
        if not value:
            return {}
        if not isinstance(value, str):
            return None
        try:
            decrypted = enc.decrypt_json(value, tenant_id=tenant_id)
        except (RuntimeError, ValueError, TypeError):
            return None
        return decrypted or {}

    async def verify_ledger(self, tenant_id: str = "default") -> dict[str, Any]:
        """Verify PostgreSQL transaction chain integrity."""
        tenant_id = self._resolve_tenant(tenant_id)
        rows = await self._backend.execute(
            "SELECT id, project, action, detail, prev_hash, hash, timestamp "
            "FROM transactions WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        )
        expected_prev = "GENESIS"
        violations: list[dict[str, Any]] = []
        for row in rows:
            prev_hash = str(row.get("prev_hash") or "GENESIS")
            tx_hash = compute_tx_hash(
                prev_hash,
                str(row["project"]),
                str(row["action"]),
                str(row["detail"]),
                str(row["timestamp"]),
            )
            if prev_hash != expected_prev:
                violations.append({"id": row["id"], "type": "CHAIN_BREAK"})
            if tx_hash != row.get("hash"):
                violations.append({"id": row["id"], "type": "TAMPER_DETECTED"})
            expected_prev = str(row.get("hash") or expected_prev)

        roots = await self._backend.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id "
            "FROM merkle_roots WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        )
        for root in roots:
            checkpoint_rows = await self._backend.execute(
                "SELECT hash FROM transactions "
                "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                (tenant_id, root["tx_start_id"], root["tx_end_id"]),
            )
            hashes = [str(row["hash"]) for row in checkpoint_rows]
            if SovereignMerkleTree(hashes).root != root["root_hash"]:
                violations.append(
                    {
                        "id": root["id"],
                        "type": "MERKLE_ROOT_MISMATCH",
                        "start": root["tx_start_id"],
                        "end": root["tx_end_id"],
                    }
                )

        tx_count = len(rows)
        return {
            "valid": not violations,
            "violations": violations,
            "tx_checked": tx_count,
            "roots_checked": len(roots),
        }

    async def verify_vote_ledger(self, tenant_id: str = "default") -> dict[str, Any]:
        """Verify immutable vote-ledger integrity in PostgreSQL."""
        tenant_id = self._resolve_tenant(tenant_id)
        rows = await self._backend.execute(
            "SELECT id, fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp "
            "FROM vote_ledger WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        )
        violations: list[dict[str, Any]] = []
        expected_prev = _VOTE_LEDGER_GENESIS_HASH
        for row in rows:
            prev_hash = str(row.get("prev_hash") or _VOTE_LEDGER_GENESIS_HASH)
            expected_hash = self._compute_vote_hash(
                prev_hash,
                int(row["fact_id"]),
                str(row["agent_id"]),
                int(row["vote"]),
                Decimal(str(row["vote_weight"])),
                str(row["timestamp"]),
            )
            if prev_hash != expected_prev:
                violations.append({"vote_id": row["id"], "type": "CHAIN_BREAK"})
            if expected_hash != row.get("hash"):
                violations.append({"vote_id": row["id"], "type": "DATA_TAMPERING"})
            expected_prev = str(row.get("hash") or expected_prev)

        roots = await self._backend.execute(
            "SELECT id, root_hash, vote_start_id, vote_end_id "
            "FROM vote_merkle_roots WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        )
        for root in roots:
            checkpoint_rows = await self._backend.execute(
                "SELECT hash FROM vote_ledger "
                "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                (tenant_id, root["vote_start_id"], root["vote_end_id"]),
            )
            hashes = [str(row["hash"]) for row in checkpoint_rows]
            if VoteMerkleTree(hashes).root != root["root_hash"]:
                violations.append(
                    {
                        "vote_checkpoint_id": root["id"],
                        "type": "MERKLE_ROOT_MISMATCH",
                        "start": root["vote_start_id"],
                        "end": root["vote_end_id"],
                    }
                )
        return {
            "valid": not violations,
            "violations": violations,
            "votes_checked": len(rows),
            "checkpoints_checked": len(roots),
        }

    async def create_checkpoint(self, tenant_id: str = "default") -> int | None:
        """Create a Merkle checkpoint over all uncheckpointed PG transactions."""
        tenant_id = self._resolve_tenant(tenant_id)

        last_cp_rows = await self._backend.execute(
            "SELECT MAX(tx_end_id) AS max_tx FROM merkle_roots WHERE tenant_id = ?",
            (tenant_id,),
        )
        last_covered = 0
        if last_cp_rows and last_cp_rows[0].get("max_tx") is not None:
            last_covered = int(last_cp_rows[0]["max_tx"])

        rows = await self._backend.execute(
            "SELECT id, hash FROM transactions WHERE tenant_id = ? AND id > ? ORDER BY id",
            (tenant_id, last_covered),
        )
        if not rows:
            return None

        hashes = [str(row["hash"]) for row in rows]
        root_hash = SovereignMerkleTree(hashes).root
        start_id = int(rows[0]["id"])
        end_id = int(rows[-1]["id"])

        async with self._backend.connection() as conn:
            async with conn.transaction():
                checkpoint_id = await self._backend.execute_insert_with_conn(
                    conn,
                    "INSERT INTO merkle_roots "
                    "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (tenant_id, root_hash, start_id, end_id, len(rows)),
                )

        return checkpoint_id

    def __getattr__(self, name: str) -> Any:
        if self._fallback is not None:
            return getattr(self._fallback, name)
        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")
