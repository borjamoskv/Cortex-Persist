# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.causality_models import (
    EDGE_TAINTED_BY,
    Confidence,
    TaintReport,
    TaintStatus,
    _downgrade_confidence,
)

try:
    from cortex.engine.logic.atms import AtmsAdapter
except ImportError:
    AtmsAdapter = None  # type: ignore

logger = logging.getLogger("cortex.engine.causality")


class AsyncCausalGraph:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        try:
            self.atms = AtmsAdapter() if AtmsAdapter else None
        except RuntimeError as e:
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

        # 1. Look up missing hashes via DIP
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

        # 2. C5-REAL: Rust ATMS Validation
        if self.atms and fact_hash:
            try:
                self.atms.add_node(fact_hash)
                if parent_hash:
                    self.atms.add_dependency(fact_hash, parent_hash)
            except Exception as e:
                # SAGA Rollback: Reject contradictory or cycle edges
                raise RuntimeError(
                    f"ATMS Graph rejected edge {parent_hash} -> {fact_hash}: {e}"
                ) from e

        # 3. L1 Persistence: Layout-aware query build to support old/test mock schemas
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
        """
        Idea #4: Temporal Knowledge Graph query.
        "What influenced decision X in the last N hours?"
        Returns the causal ancestors with their decay and confidence.
        """
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

    async def _fact_columns(self) -> set[str]:
        cursor = await self.conn.execute("PRAGMA table_info(facts)")
        return {row[1] for row in await cursor.fetchall()}

    async def _metadata_column(self) -> str | None:
        cols = await self._fact_columns()
        if "metadata" in cols:
            return "metadata"
        if "meta" in cols:
            return "meta"
        return None

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
        floor_to_c1: bool = True,
    ) -> TaintReport:
        """Propagates causal taint (Ω₁₃) from a source fact to all descendants."""
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        meta_col = await self._metadata_column()
        fact_cols = await self._fact_columns()
        has_tenant = "tenant_id" in fact_cols

        descendant_ids = await self._get_descendant_ids(fact_id, tenant_id)
        if not descendant_ids:
            return TaintReport(source_fact_id=fact_id, affected_count=0)

        edges = await self._fetch_edges(list(descendant_ids), tenant_id)
        # Fetch data for descendants and parents
        parent_ids = {p for ps in edges.values() for p in ps}
        nodes_data = await self._fetch_nodes_data(
            list(descendant_ids | parent_ids),
            tenant_id,
            meta_col,
            has_tenant,
        )

        changes, node_states = self._process_taint_propagation(
            fact_id, descendant_ids, edges, nodes_data, floor_to_c1, now
        )

        if changes:
            await self._apply_fact_updates(changes, nodes_data, meta_col, has_tenant, tenant_id)
            await self._record_taint_edges(changes, fact_id, has_tenant, tenant_id)

        await self.conn.commit()
        return TaintReport(
            source_fact_id=fact_id,
            affected_count=len(changes),
            confidence_changes=changes,
        )

    async def _get_descendant_ids(self, fact_id: int, tenant_id: str) -> set[int]:
        """Fetch all descendants using a recursive CTE."""
        sql = """
        WITH RECURSIVE descendants AS (
            SELECT ? AS id
            UNION
            SELECT ce.fact_id
            FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.id
            WHERE ce.tenant_id = ? AND ce.edge_type != ?
        )
        SELECT id FROM descendants
        """
        ids = {fact_id}
        async with self.conn.execute(sql, (fact_id, tenant_id, EDGE_TAINTED_BY)) as cursor:
            async for row in cursor:
                ids.add(int(row[0]))
        return ids

    async def _fetch_edges(self, node_ids: list[int], tenant_id: str) -> dict[int, list[int]]:
        """Fetch causal edges for the given nodes in chunks."""
        edges: dict[int, list[int]] = {}
        chunk_size = 900
        for i in range(0, len(node_ids), chunk_size):
            chunk = node_ids[i : i + chunk_size]
            local_placeholders = ",".join(["?"] * len(chunk))
            sql = f"""
            SELECT fact_id, parent_id FROM causal_edges
            WHERE fact_id IN ({local_placeholders}) AND edge_type != ? AND tenant_id = ?
            """
            async with self.conn.execute(sql, (*chunk, EDGE_TAINTED_BY, tenant_id)) as cursor:
                async for child_id, parent_id in cursor:
                    if parent_id is not None:
                        edges.setdefault(int(child_id), []).append(int(parent_id))
        return edges

    async def _fetch_nodes_data(
        self,
        node_ids: list[int],
        tenant_id: str,
        meta_col: str | None,
        has_tenant: bool,
    ) -> dict[int, dict[str, Any]]:
        """Fetch confidence and metadata for all relevant nodes."""
        nodes_data: dict[int, dict[str, Any]] = {}
        chunk_size = 900
        enc = get_default_encrypter()

        for i in range(0, len(node_ids), chunk_size):
            chunk = node_ids[i : i + chunk_size]
            local_placeholders = ",".join(["?"] * len(chunk))

            fact_sql = "SELECT id, confidence"
            if meta_col:
                fact_sql += f", {meta_col}"
            fact_sql += f" FROM facts WHERE id IN ({local_placeholders})"

            params = list(chunk)
            if has_tenant:
                fact_sql += " AND tenant_id = ?"
                params.append(tenant_id)  # pyright: ignore[reportArgumentType]

            async with self.conn.execute(fact_sql, params) as cursor:
                async for row in cursor:
                    fid = int(row[0])
                    conf = row[1] or "C5"
                    raw_meta = row[2] if meta_col and len(row) > 2 else "{}"

                    meta, is_json, is_encrypted = self._parse_metadata(raw_meta, tenant_id, enc)
                    nodes_data[fid] = {
                        "confidence": conf,
                        "metadata": meta,
                        "is_json": is_json,
                        "is_encrypted": is_encrypted,
                        "raw_meta": raw_meta,
                    }
        return nodes_data

    def _parse_metadata(
        self, raw_meta: str, tenant_id: str, enc: Any
    ) -> tuple[dict[str, Any], bool, bool]:
        """Helper to decrypt and parse metadata JSON."""
        if not raw_meta:
            return {}, False, False

        if isinstance(raw_meta, str) and raw_meta.startswith(enc.PREFIX):
            try:
                meta = enc.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
                return meta, True, True
            except (ValueError, TypeError):
                logger.warning("Failed to decrypt metadata")
                return {}, False, False

        try:
            meta = json.loads(raw_meta)
            return meta, True, False
        except (TypeError, json.JSONDecodeError):
            return {"_raw": raw_meta}, False, False

    def _process_taint_propagation(
        self,
        source_id: int,
        descendant_ids: set[int],
        edges: dict[int, list[int]],
        nodes_data: dict[int, dict[str, Any]],
        floor_to_c1: bool,
        timestamp: str,
    ) -> tuple[list[dict[str, Any]], dict[int, TaintStatus]]:
        """BFS traversal to compute new states and confidence levels."""
        node_states: dict[int, TaintStatus] = {source_id: TaintStatus.TAINTED}
        children_map: dict[int, list[int]] = {}
        for child, parents in edges.items():
            for parent in parents:
                children_map.setdefault(parent, []).append(child)

        queue = deque([source_id])
        visited: set[int] = {source_id}
        changes: list[dict[str, Any]] = []

        while queue:
            curr_id = queue.popleft()
            data = nodes_data.get(curr_id)
            if not data:
                continue

            old_conf = data["confidence"]
            new_status = self._derive_node_status(
                curr_id, source_id, edges, nodes_data, node_states
            )
            node_states[curr_id] = new_status

            new_conf = old_conf
            if new_status != TaintStatus.CLEAN:
                new_conf = (
                    Confidence.C1.value if floor_to_c1 else _downgrade_confidence(old_conf, 1)
                )

            if new_conf != old_conf or new_status != TaintStatus.CLEAN:
                if data["is_json"]:
                    data["metadata"].update(
                        {
                            "taint_status": new_status.value,
                            "tainted_by": source_id,
                            "taint_timestamp": timestamp,
                        }
                    )

                changes.append(
                    {
                        "fact_id": curr_id,
                        "old_confidence": old_conf,
                        "new_confidence": new_conf,
                        "status": new_status.value,
                    }
                )

            for child_id in children_map.get(curr_id, []):
                if child_id not in visited and child_id in descendant_ids:
                    visited.add(child_id)
                    queue.append(child_id)

        return changes, node_states

    def _derive_node_status(
        self,
        curr_id: int,
        source_id: int,
        edges: dict[int, list[int]],
        nodes_data: dict[int, dict[str, Any]],
        node_states: dict[int, TaintStatus],
    ) -> TaintStatus:
        """Determines the TaintStatus of a node based on its parents."""
        if curr_id == source_id:
            return TaintStatus.TAINTED

        parents = edges.get(curr_id, [])
        if not parents:
            return TaintStatus.CLEAN

        p_states = []
        for pid in parents:
            if pid in node_states:
                p_states.append(node_states[pid])
            else:
                p_meta = nodes_data.get(pid, {}).get("metadata", {})
                p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                p_states.append(
                    TaintStatus(p_status)
                    if p_status in TaintStatus._value2member_map_
                    else TaintStatus.CLEAN
                )

        if all(s == TaintStatus.TAINTED for s in p_states):
            return TaintStatus.TAINTED
        if any(s in (TaintStatus.TAINTED, TaintStatus.SUSPECT) for s in p_states):
            return TaintStatus.SUSPECT
        return TaintStatus.CLEAN

    async def _apply_fact_updates(
        self,
        changes: list[dict[str, Any]],
        nodes_data: dict[int, dict[str, Any]],
        meta_col: str | None,
        has_tenant: bool,
        tenant_id: str,
    ) -> None:
        """Execute batch updates to the facts table."""
        fact_updates: list[tuple[Any, ...]] = []
        enc = get_default_encrypter()

        for chg in changes:
            fid = chg["fact_id"]
            data = nodes_data[fid]
            new_conf = chg["new_confidence"]

            if meta_col:
                if data["is_encrypted"]:
                    payload = enc.encrypt_json(data["metadata"], tenant_id=tenant_id)
                elif data["is_json"]:
                    payload = json.dumps(data["metadata"])
                else:
                    payload = data.get("raw_meta", "")
                row = (new_conf, payload, fid)
            else:
                row = (new_conf, fid)

            if has_tenant:
                row = (*row, tenant_id)
            fact_updates.append(row)

        sql = "UPDATE facts SET confidence = ?"
        if meta_col:
            sql += f", {meta_col} = ?"
        sql += " WHERE id = ?"
        if has_tenant:
            sql += " AND tenant_id = ?"

        await self.conn.executemany(sql, fact_updates)

    async def _record_taint_edges(
        self,
        changes: list[dict[str, Any]],
        source_id: int,
        has_tenant: bool,
        tenant_id: str,
    ) -> None:
        """Log causal taint edges for auditability."""
        params = []
        for chg in changes:
            if chg["fact_id"] == source_id:
                continue

            row = [chg["fact_id"], source_id, None, EDGE_TAINTED_BY, None]
            if has_tenant:
                row.append(tenant_id)
            params.append(tuple(row))

        if not params:
            return

        sql = (
            """
        INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """
            if has_tenant
            else """
        INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project)
        VALUES (?, ?, ?, ?, ?)
        """
        )
        await self.conn.executemany(sql, params)

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
