# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3
from collections import deque
from typing import Any

import aiosqlite

from cortex.engine.causality_models import (
    EpistemicStatus,
    LedgerEvent,
    TaintReport,
)

try:
    from cortex.engine.logic.atms import AtmsAdapter
except ImportError:
    AtmsAdapter = None  # type: ignore

logger = logging.getLogger("cortex.engine.causal.graph")

class CausalGraph:
    def __init__(self) -> None:
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        return self._events[event_id]

    def add_event(self, event: LedgerEvent) -> None:
        self._events[event.event_id] = event
        self._children.setdefault(event.event_id, [])
        for parent_id in event.parent_ids:
            self._children.setdefault(parent_id, []).append(event.event_id)

    def get_descendants(self, node_id: str) -> list[str]:
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
    queue = deque([(refuted_event_id, 0)])
    visited: set[str] = set()

    while queue:
        node_id, depth = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        try:
            event = graph[node_id]
        except KeyError:
            continue

        if depth == 0:
            event.status = EpistemicStatus.REFUTED
            event.trust_score = 0.0
        else:
            event.trust_score = max(0.0, event.trust_score * (1.0 - decay / max(depth, 1)))
            event.tainted = True

        for child_id in graph.get_descendants(node_id):
            if child_id not in visited:
                queue.append((child_id, depth + 1))


class AsyncCausalGraph:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        try:
            self.atms = AtmsAdapter() if AtmsAdapter else None
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"Rust ATMS disabled: {e}")
            self.atms = None

    async def ensure_table(self, *, commit: bool = True) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS causal_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER NOT NULL,
                parent_id INTEGER,
                signal_id INTEGER,
                edge_type TEXT NOT NULL DEFAULT 'triggered_by',
                confidence REAL NOT NULL DEFAULT 1.0,
                agent_id TEXT,
                project TEXT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                fact_hash TEXT,
                parent_hash TEXT,
                FOREIGN KEY (fact_id) REFERENCES facts(id)
            )
            """
        )
        cols = await self._causal_edge_columns()
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_fact ON causal_edges(fact_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_parent ON causal_edges(parent_id)"
        )
        if "tenant_id" in cols:
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_causal_tenant ON causal_edges(tenant_id)"
            )
        if "fact_hash" in cols:
            await self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_causal_edges_hash ON causal_edges(fact_hash)"
            )
        if commit:
            await self.conn.commit()

    async def _causal_edge_columns(self) -> set[str]:
        cursor = await self.conn.execute("PRAGMA table_info(causal_edges)")
        rows = await cursor.fetchall()
        return {str(row[1]) for row in rows}

    async def record_edge(
        self,
        fact_id: int,
        parent_id: int | None = None,
        signal_id: int | None = None,
        edge_type: str = "triggered_by",
        confidence: float = 1.0,
        agent_id: str | None = None,
        project: str | None = None,
        tenant_id: str = "default",
        fact_hash: str | None = None,
        parent_hash: str | None = None,
    ) -> None:
        await self.ensure_table(commit=False)


        if not fact_hash:
            try:
                async with self.conn.execute(
                    "SELECT fact_hash FROM facts WHERE id = ?", (fact_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    fact_hash = row[0] if row else None
            except sqlite3.OperationalError:
                pass

        if parent_id and not parent_hash:
            try:
                async with self.conn.execute(
                    "SELECT fact_hash FROM facts WHERE id = ?", (parent_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    parent_hash = row[0] if row else None
            except sqlite3.OperationalError:
                pass

        if self.atms and fact_hash:
            try:
                self.atms.add_node(fact_hash)
                if parent_hash:
                    self.atms.add_dependency(fact_hash, parent_hash)
            except Exception as e:
                raise RuntimeError(
                    f"ATMS Graph rejected edge {parent_hash} -> {fact_hash}: {e}"
                ) from e

        cols = await self._causal_edge_columns()
        payload = []
        payload.append(("fact_id", fact_id))
        if parent_id is not None:
            payload.append(("parent_id", parent_id))
        if signal_id is not None:
            payload.append(("signal_id", signal_id))
        payload.append(("edge_type", edge_type))
        if "confidence" in cols:
            payload.append(("confidence", confidence))
        if "agent_id" in cols and agent_id is not None:
            payload.append(("agent_id", agent_id))
        if "project" in cols and project is not None:
            payload.append(("project", project))
        if "tenant_id" in cols:
            payload.append(("tenant_id", tenant_id))
        if "fact_hash" in cols and fact_hash is not None:
            payload.append(("fact_hash", fact_hash))
        if "parent_hash" in cols and parent_hash is not None:
            payload.append(("parent_hash", parent_hash))

        columns_sql = ", ".join(col for col, _ in payload)
        placeholders_sql = ", ".join("?" for _ in payload)
        values = [val for _, val in payload]

        await self.conn.execute(
            f"INSERT INTO causal_edges ({columns_sql}) VALUES ({placeholders_sql})",
            values,
        )

    async def temporal_causal_chain(
        self,
        target_fact_id: int,
        hours_lookback: int = 24,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        sql = """
        WITH RECURSIVE causal_path AS (
            SELECT 
                ce.parent_id as ancestor_id,
                ce.fact_id as child_id,
                ce.edge_type,
                ce.confidence,
                ce.agent_id,
                ce.created_at as edge_time,
                1 as depth
            FROM causal_edges ce
            WHERE ce.fact_id = ? AND ce.tenant_id = ?
              AND ce.created_at >= datetime('now', ?)
              AND ce.parent_id IS NOT NULL

            UNION ALL

            SELECT 
                ce.parent_id as ancestor_id,
                ce.fact_id as child_id,
                ce.edge_type,
                ce.confidence * cp.confidence as confidence,
                ce.agent_id,
                ce.created_at as edge_time,
                cp.depth + 1 as depth
            FROM causal_edges ce
            JOIN causal_path cp ON ce.fact_id = cp.ancestor_id
            WHERE ce.tenant_id = ?
              AND ce.created_at >= datetime('now', ?)
              AND ce.parent_id IS NOT NULL
        )
        SELECT 
            cp.ancestor_id,
            cp.child_id,
            cp.edge_type,
            cp.confidence,
            cp.agent_id,
            cp.edge_time,
            cp.depth,
            f.content as ancestor_content,
            f.decay_half_life
        FROM causal_path cp
        JOIN facts f ON cp.ancestor_id = f.id
        ORDER BY cp.depth ASC;
        """
        time_modifier = f"-{hours_lookback} hours"
        chain = []
        async with self.conn.execute(
            sql, (target_fact_id, tenant_id, time_modifier, tenant_id, time_modifier)
        ) as cursor:
            async for row in cursor:
                chain.append(
                    {
                        "ancestor_id": row[0],
                        "child_id": row[1],
                        "edge_type": row[2],
                        "confidence": row[3],
                        "agent_id": row[4],
                        "edge_time": row[5],
                        "depth": row[6],
                        "content": row[7],
                        "decay_half_life": row[8],
                    }
                )
        return chain

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
        floor_to_c1: bool = True,
    ) -> TaintReport:
        from cortex.engine.causal.taint_propagation import TaintPropagator
        propagator = TaintPropagator(self.conn)
        return await propagator.propagate_taint(fact_id, tenant_id, floor_to_c1)

    async def calculate_blast_radius(self, fact_id: int, tenant_id: str) -> int:
        sql = """
        WITH RECURSIVE descendants AS (
            SELECT fact_id FROM causal_edges
            WHERE parent_id = ? AND tenant_id = ?
            UNION
            SELECT ce.fact_id FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.fact_id
            WHERE ce.tenant_id = ?
        )
        SELECT COUNT(DISTINCT fact_id) FROM descendants
        """
        async with self.conn.execute(sql, (fact_id, tenant_id, tenant_id)) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
