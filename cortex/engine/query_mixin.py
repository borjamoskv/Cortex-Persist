"""Query mixin — search, recall, history, reconstruct_state, stats."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN, EngineMixinBase
from cortex.memory.temporal import build_temporal_filter_params, time_travel_filter
from cortex.search import SearchResult, hybrid_search, semantic_search, text_search

__all__ = ["QueryMixin"]

logger = logging.getLogger("cortex")


class QueryMixin(EngineMixinBase):
    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve all active facts, optionally filtered by project or types."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            query = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
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
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]  # type: ignore[reportAttributeAccessIssue]

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        project: str | None = None,
        top_k: int = 5,
        as_of: str | None = None,
        graph_depth: int = 0,
        fuse: bool = True,
        fast_mode: bool | None = None,
        **kwargs,
    ) -> list[SearchResult]:
        """Perform semantic or hybrid search with optional Graph-RAG context.

        Speed Optimization (Kairos-Ω):
        - If query is simple (keywords) or fast_mode=True, skip model load and use FTS5.
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        # Auto-detect fast mode: queries with 1-2 words are often keywords
        is_simple = len(query.split()) <= 2
        if fast_mode is None:
            fast_mode = is_simple

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            if fast_mode:
                # 100x Faster Path: No model load, pure FTS5
                return await text_search(
                    conn,
                    query,
                    tenant_id=tenant_id,
                    project=project,
                    limit=top_k,
                    as_of=as_of,
                    **kwargs,
                )

            embedder = self._get_embedder()  # type: ignore[reportAttributeAccessIssue]
            query_embedding = embedder.embed(query)

            if fuse:
                results = await hybrid_search(
                    conn,
                    query,
                    query_embedding,
                    top_k=top_k,
                    tenant_id=tenant_id,
                    project=project,
                    as_of=as_of,
                    **kwargs,
                )
            else:
                results = await semantic_search(
                    conn,
                    query_embedding,
                    top_k=top_k,
                    tenant_id=tenant_id,
                    project=project,
                    as_of=as_of,
                    **kwargs,
                )

            # Add graph context if requested (Wave 4: Graph-RAG)
            if results and graph_depth > 0:
                from cortex.graph import extract_entities, get_context_subgraph

                entities = extract_entities(query)
                seeds = [e["name"] for e in entities]
                if seeds:
                    subgraph = await get_context_subgraph(conn, seeds, depth=graph_depth)
                    results[0].graph_context = {"graph": subgraph, "seeds": seeds}

            return results

    async def hybrid_search(self, *args, **kwargs):
        """Unified hybrid search interface."""
        return await text_search(self, *args, **kwargs)  # type: ignore[reportArgumentAccessIssue]

    async def get_fact(self, fact_id: int, tenant_id: str = "default") -> dict[str, Any] | None:
        """Retrieve a specific fact by ID and tenant."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            query = f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ? AND f.tenant_id = ?"
            async with conn.execute(query, (fact_id, tenant_id)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_fact(row, tenant_id=tenant_id) if row else None  # type: ignore[reportAttributeAccessIssue]

    async def recall(
        self,
        project: str,
        limit: int | None = None,
        tenant_id: str = "default",
        fact_type: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """High-level recall with scoring and temporal relevance."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            query = f"""
                SELECT {FACT_COLUMNS}
                {FACT_JOIN}
                WHERE f.tenant_id = ? AND f.project = ? AND f.valid_until IS NULL
                AND f.is_quarantined = 0 AND f.is_tombstoned = 0
            """
            params: list = [tenant_id, project]

            if fact_type:
                query += " AND f.fact_type = ?"
                params.append(fact_type)

            # Unified Scoring: Bayesian reputation + Temporal decay
            query += """
                ORDER BY (
                    f.consensus_score * 0.8
                    + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2
                ) DESC, f.fact_type, f.created_at DESC
            """

            if limit:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]  # type: ignore[reportAttributeAccessIssue]

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[dict[str, Any]]:
        """Visualización histórica: hechos activos, borrados o actualizados."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            if as_of:
                clause, params = build_temporal_filter_params(as_of, table_alias="f")
                query = (
                    f"SELECT {FACT_COLUMNS} {FACT_JOIN} "  # nosec B608 — parameterized query
                    f"WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 AND {clause} "
                    "ORDER BY f.valid_from DESC"
                )
                cursor = await conn.execute(query, (tenant_id, project, *params))
            else:
                query = (
                    f"SELECT {FACT_COLUMNS} {FACT_JOIN} "  # nosec B608 — parameterized query
                    "WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 "
                    "ORDER BY f.valid_from DESC"
                )
                cursor = await conn.execute(query, (tenant_id, project))
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]  # type: ignore[reportAttributeAccessIssue]

    async def reconstruct_state(
        self,
        project: str,
        tenant_id: str = "default",
        tx_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Reconstruct the state of a project at a specific transaction ID."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            if not tx_id:
                return await self.recall(project, tenant_id=tenant_id)

            # Check transaction existence and get its time
            async with conn.execute(
                "SELECT created_at FROM transactions WHERE id = ? AND tenant_id = ?",
                (tx_id, tenant_id),
            ) as cursor:
                tx = await cursor.fetchone()
                if not tx:
                    raise ValueError(f"Transaction {tx_id} not found for tenant {tenant_id}")

            tx_time = tx[0]

            query = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "  # nosec B608 — static constants
                "WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 "
                "  AND (f.created_at <= ? "
                "  AND (f.valid_until IS NULL OR f.valid_until > ?)) "
            )
            params = [tenant_id, project, tx_time, tx_time]

            query += " ORDER BY f.id ASC"
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]  # type: ignore[reportAttributeAccessIssue]

    async def time_travel(
        self,
        tenant_id: str = "default",
        tx_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the whole world state at a specific transaction."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            clause, params = time_travel_filter(tx_id, table_alias="f")
            query = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                f"WHERE f.tenant_id = ? AND f.is_tombstoned = 0 AND {clause}"
            )
            # nosec B608 — parameterized via temporal builder

            query += " ORDER BY f.id ASC"
            cursor = await conn.execute(query, [tenant_id, *params])
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]  # type: ignore[reportAttributeAccessIssue]

    async def stats(self) -> dict:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            async with conn.execute("SELECT COUNT(*) FROM facts") as cursor:
                total = (await cursor.fetchone())[0]
            async with conn.execute(
                "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"
            ) as cursor:
                active = (await cursor.fetchone())[0]
            async with conn.execute(
                "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL"
            ) as cursor:
                projects = [p[0] for p in await cursor.fetchall()]
            async with conn.execute("SELECT COUNT(*) FROM transactions") as cursor:
                tx_count = (await cursor.fetchone())[0]

            try:
                async with conn.execute("SELECT COUNT(*) FROM fact_embeddings") as cursor:
                    embeddings = (await cursor.fetchone())[0]
            except (sqlite3.Error, OSError, ValueError):
                embeddings = 0

            async with conn.execute(
                "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
            ) as cursor:
                types = dict(await cursor.fetchall())

            # Causal chain coverage (zero-cost: indexed column)
            try:
                async with conn.execute(
                    "SELECT COUNT(*) FROM facts "
                    "WHERE parent_decision_id IS NOT NULL "
                    "AND valid_until IS NULL"
                ) as cursor:
                    causal_facts = (await cursor.fetchone())[0]
            except (sqlite3.Error, OSError):
                causal_facts = 0

            # Database size via PRAGMA (zero-overhead, no filesystem stat needed)
            try:
                async with conn.execute(
                    "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
                ) as cursor:
                    row = await cursor.fetchone()
                    db_size_bytes = row[0] if row else 0
            except (sqlite3.Error, OSError):
                db_size_bytes = 0
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

            return {
                "total_facts": total,
                "active_facts": active,
                "deprecated_facts": total - active,
                "causal_facts": causal_facts,
                "orphan_facts": active - causal_facts,
                "projects": projects,
                "project_count": len(projects),
                "types": types,
                "transactions": tx_count,
                "embeddings": embeddings,
                "db_size_mb": db_size_mb,
                "db_path": str(getattr(self, "_db_path", "unknown")),
            }

    async def graph(self, project: str | None = None):
        """Get entity graph for a project."""
        from cortex.graph import get_graph

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await get_graph(conn, project)

    async def query_entity(
        self,
        name: str,
        project: str | None = None,
    ) -> list[dict]:
        """Query a specific entity by name."""
        from cortex.graph import query_entity

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await query_entity(conn, name, project)  # type: ignore[reportReturnType]

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> list[dict]:
        """Find paths between two entities."""
        from cortex.graph import find_path

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await find_path(conn, source, target, max_depth)

    async def get_context_subgraph(
        self,
        seeds: list[str],
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict:
        """Retrieve a subgraph context for RAG."""
        from cortex.graph import get_context_subgraph

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await get_context_subgraph(conn, seeds, depth, max_nodes)

    async def get_causal_chain(
        self,
        fact_id: int,
        direction: str = "down",
        max_depth: int = 10,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Traverse the parent_decision_id causal DAG.

        Args:
            fact_id: Starting fact ID.
            direction: 'up' (toward root) or 'down' (toward leaves).
            max_depth: Maximum recursion depth (default: 10).
            tenant_id: Tenant scope.

        Returns:
            List of fact dicts ordered by depth (0 = starting fact).
        """
        if direction == "up":
            # Follow parent_decision_id upward toward root
            sql = """
                WITH RECURSIVE chain(id, depth) AS (
                    SELECT id, 0 FROM facts
                    WHERE id = ? AND tenant_id = ?
                    UNION ALL
                    SELECT f.parent_decision_id, c.depth + 1
                    FROM facts f JOIN chain c ON f.id = c.id
                    WHERE f.parent_decision_id IS NOT NULL
                        AND c.depth < ?
                )
                SELECT id, depth FROM chain ORDER BY depth
            """
        else:
            sql = """
                WITH RECURSIVE chain(id, depth) AS (
                    SELECT id, 0 FROM facts
                    WHERE id = ? AND tenant_id = ?
                    UNION ALL
                    SELECT f.id, c.depth + 1
                    FROM facts f JOIN chain c
                        ON f.parent_decision_id = c.id
                    WHERE c.depth < ?
                )
                SELECT id, depth FROM chain ORDER BY depth
            """

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            cursor = await conn.execute(sql, (fact_id, tenant_id, max_depth))
            chain_ids = await cursor.fetchall()

            if not chain_ids:
                return []

            # Fetch full fact data for each ID in the chain
            id_list = [row[0] for row in chain_ids if row[0] is not None]
            depth_map = {
                row[0]: row[1] for row in chain_ids if row[0] is not None
            }

            if not id_list:
                return []

            placeholders = ", ".join("?" for _ in id_list)
            cursor = await conn.execute(
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                f"WHERE f.id IN ({placeholders})",
                id_list,
            )
            rows = await cursor.fetchall()
            facts = [
                self._row_to_fact(row, tenant_id=tenant_id)  # type: ignore[reportAttributeAccessIssue]
                for row in rows
            ]

            # Annotate with depth and sort
            for f in facts:
                f["causal_depth"] = depth_map.get(f["id"], 0)
            facts.sort(key=lambda f: f["causal_depth"])

            return facts
