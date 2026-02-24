"""Fact Sovereign Layer — FactManager for CORTEX."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

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
    ) -> int:
        """Sovereign Store: Delegates to engine with pre-validation."""
        # Manager-specific validation
        if len(content.strip()) < self.MIN_CONTENT_LENGTH:
            raise ValueError(
                f"content too short ({len(content.strip())} chars, min {self.MIN_CONTENT_LENGTH})"
            )

        from cortex.engine.store_mixin import StoreMixin

        conn = await self.engine.get_conn()
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

    async def recall(
        self, project: str, tenant_id: str = "default", limit: int | None = None, offset: int = 0
    ) -> list[Fact]:
        conn = await self.engine.get_conn()
        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            f"WHERE f.tenant_id = ? AND f.project = ? AND f.valid_until IS NULL "
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
    ) -> int:
        """Sovereign Update: Calls StoreMixin.update directly on the engine."""
        from cortex.engine.store_mixin import StoreMixin

        return await StoreMixin.update(
            self.engine, fact_id=fact_id, content=content, tags=tags, meta=meta
        )

    async def deprecate(self, fact_id: int, reason: str | None = None) -> bool:
        """Sovereign Deprecation: Calls StoreMixin.deprecate directly on the engine."""
        from cortex.engine.store_mixin import StoreMixin
        return await StoreMixin.deprecate(self.engine, fact_id=fact_id, reason=reason)

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
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                f"WHERE f.tenant_id = ? AND f.project = ? AND {clause} "
                "ORDER BY f.valid_from DESC"
            )
            cursor = await conn.execute(query, [tenant_id, project] + params)
        else:
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                f"WHERE f.tenant_id = ? AND f.project = ? "
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
            f"WHERE f.tenant_id = ? AND {clause}"
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
