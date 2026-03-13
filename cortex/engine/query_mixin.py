"""Query mixin — recall, history, time-travel, causal chains, stats.

Note: ``search()`` is NOT defined here. The canonical search implementation
lives in ``SearchMixin`` which provides hybrid search with graceful fallback
and Graph-RAG enrichment.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN, EngineMixinBase
from cortex.memory.temporal import build_temporal_filter_params, time_travel_filter
from cortex.search import SearchResult

__all__ = ["QueryMixin"]

logger = logging.getLogger("cortex")


class QueryMixin(EngineMixinBase):
    """Query Layer — Recall, History, Time-Travel, Graph, and Stats.

    Provides all read-path operations against the fact store:
    - ``recall()``: Bayesian-scored retrieval with temporal decay.
    - ``history()``: Full temporal audit trail (active + deprecated).
    - ``reconstruct_state()``: Point-in-time state reconstruction.
    - ``time_travel()``: World-state snapshot at any transaction.
    - ``get_causal_chain()``: DAG traversal via ``parent_decision_id``.
    - ``stats()``: O(1) indexed aggregate metrics.
    """

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve all active facts, optionally filtered by project or types."""
        tenant_id = self._resolve_tenant(tenant_id)

        async with self.session() as conn:
            query = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                "WHERE f.tenant_id = ? AND "
                "(json_extract(f.meta, '$.is_quarantined') IS NULL OR "
                "json_extract(f.meta, '$.is_quarantined') = 0) "
                "AND f.is_tombstoned = 0"
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
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

    # NOTE: search() is provided by SearchMixin, not QueryMixin.
    # This avoids duplication and ensures the canonical search path
    # (with fallback + Graph-RAG enrichment) is always used.

    async def hybrid_search(
        self,
        query: str,
        tenant_id: str = "default",
        project: str | None = None,
        top_k: int = 5,
        as_of: str | None = None,
        **kwargs,
    ) -> list[SearchResult]:
        """Hybrid search combining vector similarity + FTS5 text matching.

        Delegates to the canonical ``search()`` method (from ``SearchMixin``)
        which provides automatic fallback and Graph-RAG enrichment.
        """
        return await self.search(
            query=query,
            tenant_id=tenant_id,
            project=project,
            top_k=top_k,
            as_of=as_of,
            **kwargs,
        )

    async def get_fact(
        self,
        fact_id: int,
        tenant_id: str = "default",
    ) -> dict[str, Any] | None:
        """Retrieve a single active or deprecated fact by primary key."""
        tenant_id = self._resolve_tenant(tenant_id)
        async with self.session() as conn:
            q = f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ? AND f.tenant_id = ?"
            async with conn.execute(q, (fact_id, tenant_id)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_fact(row, tenant_id=tenant_id) if row else None

    async def recall(
        self,
        project: str,
        limit: int | None = None,
        tenant_id: str = "default",
        fact_type: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Bayesian-scored recall with temporal decay.

        Scoring: ``consensus_score * 0.8 + temporal_proximity * 0.2``.
        Excludes quarantined and tombstoned facts.
        """
        tenant_id = self._resolve_tenant(tenant_id)
        async with self.session() as conn:
            q = (
                f"SELECT {FACT_COLUMNS} "
                f"{FACT_JOIN} "
                "WHERE f.tenant_id = ? AND f.project = ? "
                "AND (json_extract(f.meta, '$.is_quarantined') IS NULL OR "
                "json_extract(f.meta, '$.is_quarantined') = 0) "
                "AND f.is_tombstoned = 0"
            )
            params: list = [tenant_id, project]

            if fact_type:
                q += " AND f.fact_type = ?"
                params.append(fact_type)

            # Unified Scoring: Bayesian reputation + Temporal decay
            q += """
                ORDER BY (
                    coalesce(json_extract(f.meta, '$.consensus_score'), 1.0) * 0.8
                    + (1.0 / (1.0 + (
                        julianday('now') - julianday(f.created_at)
                    ))) * 0.2
                ) DESC, f.fact_type, f.created_at DESC
            """

            if limit:
                q += " LIMIT ?"
                params.append(limit)
            if offset:
                q += " OFFSET ?"
                params.append(offset)

            cursor = await conn.execute(q, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[dict[str, Any]]:
        """Full temporal audit trail — active, deprecated, and updated facts.

        Args:
            as_of: ISO timestamp to filter facts valid at that point in time.
        """
        tenant_id = self._resolve_tenant(tenant_id)

        async with self.session() as conn:
            base = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "  # nosec B608
                "WHERE f.tenant_id = ? AND f.project = ? "
                "AND f.is_tombstoned = 0"
            )
            if as_of:
                clause, tparams = build_temporal_filter_params(
                    as_of,
                    table_alias="f",
                )
                q = (
                    f"{base} AND {clause} ORDER BY "
                    "coalesce(json_extract(f.meta, '$.valid_from'), f.created_at) DESC"
                )
                cursor = await conn.execute(
                    q,
                    (tenant_id, project, *tparams),
                )
            else:
                q = (
                    f"{base} ORDER BY "
                    "coalesce(json_extract(f.meta, '$.valid_from'), f.created_at) DESC"
                )
                cursor = await conn.execute(q, (tenant_id, project))
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

    async def reconstruct_state(
        self,
        project: str,
        tenant_id: str = "default",
        tx_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Point-in-time state reconstruction at a given transaction.

        If ``tx_id`` is ``None``, returns current active state via ``recall()``.

        Raises:
            ValueError: If the transaction ID does not exist.
        """
        tenant_id = self._resolve_tenant(tenant_id)

        async with self.session() as conn:
            if not tx_id:
                return await self.recall(project, tenant_id=tenant_id)

            async with conn.execute(
                "SELECT created_at FROM transactions WHERE id = ? AND tenant_id = ?",
                (tx_id, tenant_id),
            ) as cursor:
                tx = await cursor.fetchone()
                if not tx:
                    raise ValueError(f"Transaction {tx_id} not found for tenant {tenant_id}")

            tx_time = tx[0]
            q = (
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "  # nosec B608
                "WHERE f.tenant_id = ? AND f.project = ? "
                "AND f.is_tombstoned = 0 "
                "AND f.created_at <= ? "
                "AND (f.is_tombstoned = 0 OR "
                "json_extract(f.meta, '$.tombstoned_at') > ? OR "
                "json_extract(f.meta, '$.valid_until') > ?) "
                "ORDER BY f.id ASC"
            )
            cursor = await conn.execute(
                q,
                [tenant_id, project, tx_time, tx_time, tx_time],
            )
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

    async def time_travel(
        self,
        tenant_id: str = "default",
        tx_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Global world-state snapshot at a given transaction.

        Unlike ``reconstruct_state()``, this is project-agnostic —
        it returns *all* facts across all projects at the given point.
        """
        tenant_id = self._resolve_tenant(tenant_id)

        async with self.session() as conn:
            if tx_id is None:
                q = (
                    f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                    f"WHERE f.tenant_id = ? "
                    f"AND f.is_tombstoned = 0 "
                    "ORDER BY f.id ASC"
                )
                cursor = await conn.execute(q, [tenant_id])
            else:
                clause, tparams = time_travel_filter(
                    tx_id,
                    table_alias="f",
                )
                q = (
                    f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                    f"WHERE f.tenant_id = ? "
                    f"AND f.is_tombstoned = 0 AND {clause} "
                    "ORDER BY f.id ASC"
                )  # nosec B608 — parameterized via temporal builder
                cursor = await conn.execute(q, [tenant_id, *tparams])
            rows = await cursor.fetchall()
            return [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

    async def stats(self) -> dict:
        async with self.session() as conn:
            async with conn.execute("SELECT COUNT(*) FROM facts") as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0
            async with conn.execute("SELECT COUNT(*) FROM facts WHERE is_tombstoned = 0") as cursor:
                row = await cursor.fetchone()
                active = row[0] if row else 0
            async with conn.execute(
                "SELECT DISTINCT project FROM facts WHERE is_tombstoned = 0"
            ) as cursor:
                projects = [p[0] for p in await cursor.fetchall()]
            async with conn.execute("SELECT COUNT(*) FROM transactions") as cursor:
                row = await cursor.fetchone()
                tx_count = row[0] if row else 0

            try:
                async with conn.execute("SELECT COUNT(*) FROM fact_embeddings") as cursor:
                    row = await cursor.fetchone()
                    embeddings = row[0] if row else 0
            except (sqlite3.Error, OSError, ValueError):
                embeddings = 0

            async with conn.execute(
                "SELECT fact_type, COUNT(*) FROM facts WHERE is_tombstoned = 0 GROUP BY fact_type"
            ) as cursor:
                types = {row[0]: row[1] for row in await cursor.fetchall()}

            # Causal chain coverage (zero-cost: indexed column)
            try:
                async with conn.execute(
                    "SELECT COUNT(*) FROM facts "
                    "WHERE json_extract(meta, '$.parent_decision_id') IS NOT NULL "
                    "AND is_tombstoned = 0"
                ) as cursor:
                    row = await cursor.fetchone()
                    causal_facts = row[0] if row else 0
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

    async def graph(self, project: str | None = None, tenant_id: str = "default"):
        """Get entity graph for a project."""
        tenant_id = self._resolve_tenant(tenant_id)
        from cortex.graph import get_graph

        async with self.session() as conn:
            return await get_graph(conn, project, tenant_id=tenant_id)

    async def query_entity(
        self,
        name: str,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any] | None:
        """Query a specific entity by name."""
        tenant_id = self._resolve_tenant(tenant_id)
        from cortex.graph import query_entity

        async with self.session() as conn:
            return await query_entity(
                conn,
                name,
                project,
                tenant_id=tenant_id,
            )

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
        tenant_id: str = "default",
    ) -> list[dict]:
        """Find paths between two entities."""
        tenant_id = self._resolve_tenant(tenant_id)
        from cortex.graph import find_path

        async with self.session() as conn:
            return await find_path(conn, source, target, max_depth, tenant_id=tenant_id)

    async def get_context_subgraph(
        self,
        seeds: list[str],
        depth: int = 2,
        max_nodes: int = 50,
        tenant_id: str = "default",
    ) -> dict:
        """Retrieve a subgraph context for RAG."""
        tenant_id = self._resolve_tenant(tenant_id)
        from cortex.graph import get_context_subgraph

        async with self.session() as conn:
            return await get_context_subgraph(conn, seeds, depth, max_nodes, tenant_id=tenant_id)

    async def get_causal_chain(
        self,
        fact_id: int,
        direction: str = "down",
        max_depth: int = 10,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Traverse the ``parent_decision_id`` causal DAG.

        Args:
            fact_id: Starting fact ID.
            direction: ``'up'`` (toward root) or ``'down'`` (leaves).
            max_depth: Maximum recursion depth (default: 10).
            tenant_id: Tenant scope.

        Returns:
            Facts ordered by depth (0 = starting fact).
        """
        tenant_id = self._resolve_tenant(tenant_id)

        if direction == "up":
            sql = """
                WITH RECURSIVE chain(id, depth) AS (
                    SELECT id, 0 FROM facts
                    WHERE id = ? AND tenant_id = ?
                    UNION ALL
                    SELECT json_extract(f.meta, '$.parent_decision_id'), c.depth + 1
                    FROM facts f JOIN chain c ON f.id = c.id
                    WHERE json_extract(f.meta, '$.parent_decision_id') IS NOT NULL
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
                        ON json_extract(f.meta, '$.parent_decision_id') = c.id
                    WHERE c.depth < ?
                )
                SELECT id, depth FROM chain ORDER BY depth
            """

        async with self.session() as conn:
            cursor = await conn.execute(
                sql,
                (fact_id, tenant_id, max_depth),
            )
            chain_ids = await cursor.fetchall()

            if not chain_ids:
                return []

            id_list = [row[0] for row in chain_ids if row[0] is not None]
            depth_map = {row[0]: row[1] for row in chain_ids if row[0] is not None}

            if not id_list:
                return []

            placeholders = ", ".join("?" for _ in id_list)
            cursor = await conn.execute(
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
                f"WHERE f.id IN ({placeholders}) "
                "AND f.tenant_id = ?",
                [*id_list, tenant_id],
            )
            rows = await cursor.fetchall()
            facts = [self._row_to_fact(row, tenant_id=tenant_id) for row in rows]

            for f in facts:
                f["causal_depth"] = depth_map.get(f["id"], 0)
            facts.sort(key=lambda x: x["causal_depth"])

            return facts
