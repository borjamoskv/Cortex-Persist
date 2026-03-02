"""Fact Sovereign Layer — FactManager for CORTEX."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from cortex.engine.models import Fact, row_to_fact
from cortex.memory.temporal import build_temporal_filter_params, now_iso

__all__ = ["FactManager"]

logger = logging.getLogger("cortex.facts")

_FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
    "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
    "f.created_at, f.updated_at, f.tx_id, t.hash"
)
_FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"


class IngestionFact(BaseModel):
    """V8 Guardrail: Strict input validation before processing."""

    project: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
    tenant_id: str = Field(..., min_length=1)
    confidence: str = Field(..., pattern=r"^(C[1-5]|stated|inferred)$")
    # Mapping 'source' parameter to 'provenance' conceptually
    source: str = Field(..., min_length=1, description="Provenance / Data origin")


class FactManager:
    """Manages the full lifecycle and retrieval of facts."""

    def __init__(self, engine):
        self.engine = engine

    # Minimum content length to prevent garbage facts.
    MIN_CONTENT_LENGTH = 10

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
        commit: bool = True,
        tx_id: int | None = None,
        conn: Any | None = None,
        **kwargs,
    ) -> int:
        """Sovereign Store: Delegates to engine with pre-validation."""
        conn = conn or await self.engine.get_conn()

        # Sovereign Pre-filtering Gate: Active Forgetting (#350/100)
        if (
            hasattr(self.engine, "memory")
            and self.engine.memory
            and hasattr(self.engine.memory, "thalamus")
        ):
            should_process, action, _ = await self.engine.memory.thalamus.filter(
                content=content, project_id=project, tenant_id=tenant_id, fact_type=fact_type
            )
            if not should_process:
                from cortex.routes.notch_ws import notify_notch_pruning

                await notify_notch_pruning()
                raise ValueError(f"Thalamus: Fact rejected ({action})")

        # V8 Validation Layer (Strict Pydantic)
        try:
            validated = IngestionFact(
                project=project,
                content=content,
                tenant_id=tenant_id,
                confidence=confidence,
                source=source or "cli",
            )
            # Re-assign validated properties just in case of coerced changes
            project = validated.project
            content = validated.content
            tenant_id = validated.tenant_id
            confidence = validated.confidence
            source = validated.source

            # V8 Semantic Deduplication
            if hasattr(self.engine, "embeddings") and self.engine.embeddings:
                # 1. Generate text embedding
                if hasattr(self.engine.embeddings, "embed_text"):
                    vec = await self.engine.embeddings.embed_text(content)
                    if vec:
                        # 2. Check for Similarity > 0.90 in sqlite-vec facts or embeddings
                        # Since we only evaluate, if the result is high, skip store
                        results = await self.search(
                            query=content, tenant_id=tenant_id, project=project, top_k=1
                        )
                        if results and results[0].score > 0.90:
                            logger.info(
                                "V8 Guardrail: Fact discarded - Semantic Duplicate of "
                                f"#{results[0].fact_id} (Score: {results[0].score:.2f})"
                            )
                            # We update updated_at / last_accessed
                            await conn.execute(
                                "UPDATE facts SET updated_at = ? WHERE id = ?",
                                (now_iso(), results[0].fact_id),
                            )
                            await conn.commit()
                            return results[0].fact_id
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                raise ValueError(f"Ingestion Validation Failed: {e}") from e
            logger.warning(f"V8 Deduplication check skipped or failed: {e}")

        from cortex.engine.store_mixin import StoreMixin

        return await StoreMixin._store_impl(
            self.engine,
            conn,
            project,
            content,
            tenant_id,
            fact_type,
            tags,
            confidence,
            source,
            meta,
            valid_from,
            commit,
            tx_id,
        )

    async def store_many(self, facts: list[dict]) -> list[int]:
        if not facts:
            raise ValueError("Facts list cannot be empty")

        # Validation pass before any inserts
        for i, fact in enumerate(facts):
            if "project" not in fact or not fact["project"].strip():
                raise ValueError(f"Fact at index {i} is missing project")
            if "content" not in fact or not fact["content"].strip():
                raise ValueError(f"Fact at index {i} is missing content")

        conn = await self.engine.get_conn()
        ids = []
        try:
            for fact in facts:
                tenant_id = fact.get("tenant_id", "default")
                fid = await self.store(
                    project=fact["project"],
                    content=fact["content"],
                    tenant_id=tenant_id,
                    fact_type=fact.get("fact_type", "knowledge"),
                    tags=fact.get("tags"),
                    confidence=fact.get("confidence", "stated"),
                    source=fact.get("source"),
                    meta=fact.get("meta"),
                    valid_from=fact.get("valid_from"),
                    commit=False,
                )
                ids.append(fid)
            await conn.commit()
            return ids
        except (sqlite3.Error, OSError, ValueError):
            await conn.rollback()
            raise

    async def get_fact(self, fact_id: int) -> Fact | None:
        """Retrieve any fact by ID, including deprecated ones."""
        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        return row_to_fact(row) if row else None

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        project: str | None = None,
        top_k: int = 5,
        as_of: str | None = None,
        **kwargs,
    ) -> list:
        """Sovereign Search: Calls SearchMixin.search directly.

        Avoids CortexEngine override recursion.
        """
        from cortex.engine.search_mixin import SearchMixin

        return await SearchMixin.search(
            self.engine,
            query=query,
            tenant_id=tenant_id,
            project=project,
            top_k=top_k,
            as_of=as_of,
            **kwargs,
        )

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[Fact]:
        """Retrieve all active facts, optionally filtered by project or types."""
        conn = await self.engine.get_conn()
        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            "WHERE f.tenant_id = ? AND f.valid_until IS NULL "
            "AND f.is_quarantined = 0 AND f.is_tombstoned = 0"
        )
        params: list = [tenant_id]

        if project:
            query += " AND f.project = ?"
            params.append(project)

        if fact_types:
            placeholders = ", ".join("?" for _ in fact_types)
            query += f" AND f.fact_type IN ({placeholders})"
            params.extend(fact_types)

        query += " ORDER BY f.project, f.fact_type, f.id"
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def recall(
        self, project: str, tenant_id: str = "default", limit: int | None = None, offset: int = 0
    ) -> list[Fact]:
        conn = await self.engine.get_conn()
        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            f"WHERE f.tenant_id = ? AND f.project = ? AND f.valid_until IS NULL "
            f"AND f.is_quarantined = 0 AND f.is_tombstoned = 0 "
            f"ORDER BY (f.consensus_score * 0.8 + "
            f"(1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC, "
            f"f.fact_type, f.created_at DESC"
        )
        params: list = [tenant_id, project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def update(
        self,
        fact_id: int,
        content: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
        **kwargs,
    ) -> int:
        """Sovereign Update: Calls StoreMixin.update directly on the engine."""
        from cortex.engine.store_mixin import StoreMixin

        return await StoreMixin.update(
            self.engine,
            fact_id=fact_id,
            content=content,
            tags=tags,
            meta=meta,
        )

    async def deprecate(
        self, fact_id: int, reason: str | None = None, conn: Any | None = None, **kwargs
    ) -> bool:
        """Sovereign Deprecation: Calls StoreMixin.deprecate directly on the engine."""
        from cortex.engine.store_mixin import StoreMixin

        return await StoreMixin.deprecate(
            self.engine, fact_id=fact_id, reason=reason, conn=conn, **kwargs
        )

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[Fact]:
        conn = await self.engine.get_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "  # nosec B608 — parameterized query
                f"WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 AND {clause} "
                "ORDER BY f.valid_from DESC"
            )
            cursor = await conn.execute(query, [tenant_id, project] + params)
        else:
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "  # nosec B608 — parameterized query
                f"WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 "
                "ORDER BY f.valid_from DESC"
            )
            cursor = await conn.execute(query, (tenant_id, project))
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def time_travel(
        self,
        tx_id: int,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[Fact]:
        """Reconstruct state as of transaction ID."""
        from cortex.memory.temporal import time_travel_filter

        conn = await self.engine.get_conn()
        clause, params = time_travel_filter(tx_id, table_alias="f")
        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            f"WHERE f.tenant_id = ? AND f.is_tombstoned = 0 AND {clause}"
        )
        params = [tenant_id] + params
        if project:
            query += " AND f.project = ?"
            params.append(project)
        query += " ORDER BY f.id ASC"
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def reconstruct_state(
        self,
        tx_id: int,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[Fact]:
        """Alias for time_travel for State Reconstruction Axiom."""
        return await self.time_travel(tx_id, tenant_id, project)

    async def register_ghost(self, reference: str, context: str, project: str) -> int:
        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ?", (reference, project)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        ts = now_iso()
        cursor = await conn.execute(
            "INSERT INTO ghosts (reference, context, project, status, created_at) "
            "VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, ts),
        )
        ghost_id = cursor.lastrowid
        await conn.commit()
        return ghost_id

    async def stats(self) -> dict:
        """Async gathering of fact layer statistics with zero blocking."""
        conn = await self.engine.get_conn()
        # Optimized parallel counting is possible here if needed,
        # but few queries are fast enough for sequential async.
        cursor = await conn.execute("SELECT COUNT(*) FROM facts")
        total = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
        active = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL")
        projects = [p[0] for p in await cursor.fetchall()]

        cursor = await conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        )
        types = dict(await cursor.fetchall())

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = (await cursor.fetchone())[0]

        db_size = (
            self.engine._db_path.stat().st_size / (1024 * 1024)
            if self.engine._db_path.exists()
            else 0
        )

        embeddings = 0
        try:
            cursor = await conn.execute("SELECT COUNT(*) FROM fact_embeddings")
            embeddings = (await cursor.fetchone())[0]
        except (sqlite3.Error, OSError, ValueError):
            pass

        return {
            "total_facts": total,
            "active_facts": active,
            "deprecated_facts": total - active,
            "projects": projects,
            "project_count": len(projects),
            "types": types,
            "transactions": tx_count,
            "embeddings": embeddings,
            "db_path": str(self.engine._db_path),
            "db_size_mb": round(db_size, 2),
        }

    async def graph(self, project: str | None = None):
        """Get entity graph for a project."""
        from cortex.graph import get_graph

        conn = await self.engine.get_conn()
        return await get_graph(conn, project)

    async def query_entity(self, name: str, project: str | None = None) -> dict | None:
        """Query a specific entity by name."""
        from cortex.graph import query_entity

        conn = await self.engine.get_conn()
        return await query_entity(conn, name, project)

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> list[dict]:
        """Find paths between two entities."""
        from cortex.graph import find_path

        conn = await self.engine.get_conn()
        return await find_path(conn, source, target, max_depth)

    async def get_context_subgraph(
        self,
        seeds: list[str],
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict:
        """Retrieve a subgraph context for RAG."""
        from cortex.graph import get_context_subgraph

        conn = await self.engine.get_conn()
        return await get_context_subgraph(conn, seeds, depth, max_nodes)
