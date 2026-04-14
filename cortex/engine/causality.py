"""Causal graph and taint propagation utilities for CORTEX."""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.database.core import connect
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")

__all__ = [
    "AsyncCausalGraph",
    "AsyncCausalOracle",
    "CausalGraph",
    "CausalOracle",
    "Confidence",
    "EDGE_DERIVED_FROM",
    "EDGE_TAINTED_BY",
    "EDGE_TRIGGERED_BY",
    "EDGE_UPDATED_FROM",
    "EpistemicStatus",
    "LedgerEvent",
    "TaintReport",
    "TaintStatus",
    "_downgrade_confidence",
    "link_causality",
]


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


class TaintStatus(str, Enum):
    """Tri-state causal taint (Ω₁₃)."""

    CLEAN = "clean"
    SUSPECT = "suspect"
    TAINTED = "tainted"


class Confidence(str, Enum):
    """Ordinal confidence levels C1 (lowest) -> C5 (highest)."""

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"

CONFIDENCE_ORDER: list[Confidence] = [
    Confidence.C1,
    Confidence.C2,
    Confidence.C3,
    Confidence.C4,
    Confidence.C5,
]
CONFIDENCE_LEVELS: list[str] = [c.value for c in reversed(CONFIDENCE_ORDER)]


def _downgrade_confidence(current: str, hops: int) -> str:
    """Downgrade confidence by *hops* levels (floor = C1)."""
    try:
        idx = CONFIDENCE_ORDER.index(Confidence(current))
    except ValueError:
        return Confidence.C1.value
    new_idx = max(0, idx - hops)
    return CONFIDENCE_ORDER[new_idx].value


@dataclass(frozen=True)
class TaintReport:
    """Immutable record of a taint propagation run."""

    source_fact_id: int
    affected_count: int
    confidence_changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LedgerEvent:
    event_id: str
    parent_ids: list[str]
    status: EpistemicStatus
    trust_score: float
    created_at: str
    last_revalidated_at: Optional[str] = None
    tainted: bool = False


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

    async def ensure_table(self) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS causal_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER NOT NULL,
                parent_id INTEGER,
                signal_id INTEGER,
                edge_type TEXT NOT NULL DEFAULT 'triggered_by',
                project TEXT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (fact_id) REFERENCES facts(id)
            )
            """
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_fact ON causal_edges(fact_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_parent ON causal_edges(parent_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_tenant ON causal_edges(tenant_id)"
        )
        await self.conn.commit()

    async def record_edge(
        self,
        fact_id: int,
        parent_id: Optional[int] = None,
        signal_id: Optional[int] = None,
        edge_type: str = "triggered_by",
        project: Optional[str] = None,
        tenant_id: str = "default",
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (fact_id, parent_id, signal_id, edge_type, project, tenant_id),
        )

    async def _fact_columns(self) -> set[str]:
        cursor = await self.conn.execute("PRAGMA table_info(facts)")
        return {row[1] for row in await cursor.fetchall()}

    async def _metadata_column(self) -> Optional[str]:
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
                params.append(tenant_id)

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
            except Exception:
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


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
        project: Optional[str] = None,
    ) -> Optional[int]:
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(tenant_id=tenant_id, project=project, limit=5)
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except Exception as e:  # noqa: BLE001
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
    def find_parent_signal(
        db_path: str,
        tenant_id: str = "default",
        project: Optional[str] = None,
    ) -> Optional[int]:
        try:
            with connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(tenant_id=tenant_id, project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:  # noqa: BLE001
            logger.debug("Sync causal lookup failed: %s", e)
        return None


def link_causality(
    meta: Optional[dict[str, Any]],
    signal_id: Optional[int],
) -> dict[str, Any]:
    """Attach causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m


def rowless_json(data: dict[str, Any]) -> str:
    return json.dumps(data)
