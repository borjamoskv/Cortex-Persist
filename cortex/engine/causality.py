"""Causal graph and taint propagation utilities for CORTEX."""

from __future__ import annotations

import json
import logging
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
        now = datetime.now(timezone.utc).isoformat()
        meta_col = await self._metadata_column()
        fact_cols = await self._fact_columns()
        has_tenant = "tenant_id" in fact_cols

        desc_sql = """
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
        descendant_ids: set[int] = set()
        async with self.conn.execute(desc_sql, (fact_id, tenant_id, EDGE_TAINTED_BY)) as cursor:
            async for row in cursor:
                descendant_ids.add(int(row[0]))

        if fact_id not in descendant_ids:
            descendant_ids.add(fact_id)

        if not descendant_ids:
            return TaintReport(source_fact_id=fact_id, affected_count=0, confidence_changes=[])

        node_ids = list(descendant_ids)
        edges: dict[int, list[int]] = {}
        all_node_ids = set(descendant_ids)
        chunk_size = 900
        for start in range(0, len(node_ids), chunk_size):
            chunk = node_ids[start : start + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            edge_sql = f"""
            SELECT fact_id, parent_id FROM causal_edges
            WHERE fact_id IN ({placeholders}) AND edge_type != ? AND tenant_id = ?
            """
            async with self.conn.execute(edge_sql, (*chunk, EDGE_TAINTED_BY, tenant_id)) as cursor:
                async for child_id, parent_id in cursor:
                    if parent_id is None:
                        continue
                    edges.setdefault(int(child_id), []).append(int(parent_id))
                    all_node_ids.add(int(parent_id))

        nodes_data: dict[int, dict[str, Any]] = {}
        all_nodes_list = list(all_node_ids)
        for start in range(0, len(all_nodes_list), chunk_size):
            chunk = all_nodes_list[start : start + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            if meta_col:
                fact_sql = (
                    f"SELECT id, confidence, {meta_col} FROM facts WHERE id IN ({placeholders})"
                )
            else:
                fact_sql = f"SELECT id, confidence FROM facts WHERE id IN ({placeholders})"
            params: tuple[Any, ...]
            if has_tenant:
                fact_sql += " AND tenant_id = ?"
                params = (*chunk, tenant_id)
            else:
                params = tuple(chunk)
            async with self.conn.execute(fact_sql, params) as cursor:
                async for row in cursor:
                    fid = int(row[0])
                    conf = row[1] or "C5"
                    if meta_col:
                        raw_meta = row[2] if len(row) > 2 else "{}"
                    else:
                        raw_meta = "{}"

                    is_encrypted = False
                    meta = {}
                    is_json = False

                    if raw_meta:
                        # Try to decrypt if it looks like ciphertext
                        enc = get_default_encrypter()
                        if raw_meta.startswith(enc.PREFIX):
                            try:
                                meta = enc.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
                                is_encrypted = True
                                is_json = True
                            except Exception:
                                logger.warning("Failed to decrypt metadata for fact %d", fid)
                                meta = {}
                        else:
                            try:
                                meta = json.loads(raw_meta)
                                is_json = True
                            except (TypeError, json.JSONDecodeError):
                                meta = raw_meta  # Preserve raw string if not JSON
                                is_json = False

                    nodes_data[fid] = {
                        "confidence": conf,
                        "metadata": meta,
                        "is_json": is_json,
                        "is_encrypted": is_encrypted,
                        "raw_meta": raw_meta,  # Keep track of original
                        "raw_metadata": raw_meta,
                    }

        node_states: dict[int, TaintStatus] = {fact_id: TaintStatus.TAINTED}
        children_map: dict[int, list[int]] = {}
        for child, parents in edges.items():
            for parent in parents:
                children_map.setdefault(parent, []).append(child)

        queue = deque([fact_id])
        visited: set[int] = {fact_id}
        changes: list[dict[str, Any]] = []
        fact_updates: list[tuple[Any, ...]] = []

        while queue:
            current_id = queue.popleft()
            data = nodes_data.get(current_id)
            if not data:
                continue

            old_conf = data["confidence"]
            if current_id == fact_id:
                new_conf = Confidence.C1.value
                node_states[current_id] = TaintStatus.TAINTED
            else:
                parents = edges.get(current_id, [])
                p_states: list[TaintStatus] = []
                for pid in parents:
                    if pid in node_states:
                        p_states.append(node_states[pid])
                    else:
                        p_meta = nodes_data.get(pid, {}).get("metadata", {})
                        p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                        try:
                            p_states.append(TaintStatus(p_status))
                        except ValueError:
                            p_states.append(TaintStatus.CLEAN)

                tainted_count = p_states.count(TaintStatus.TAINTED)
                suspect_count = p_states.count(TaintStatus.SUSPECT)
                total_parents = len(parents)

                if total_parents > 0 and tainted_count == total_parents:
                    node_states[current_id] = TaintStatus.TAINTED
                    hops = 1
                elif tainted_count > 0:
                    node_states[current_id] = TaintStatus.SUSPECT
                    hops = 1
                elif suspect_count > 0:
                    node_states[current_id] = TaintStatus.SUSPECT
                    hops = 1
                else:
                    node_states[current_id] = TaintStatus.CLEAN
                    hops = 0

                if hops > 0:
                    new_conf = (
                        Confidence.C1.value
                        if floor_to_c1
                        else _downgrade_confidence(old_conf, hops)
                    )
                else:
                    new_conf = old_conf

            data["confidence"] = new_conf
            if data["is_json"]:
                data["metadata"]["taint_status"] = node_states[current_id].value
                data["metadata"]["tainted_by"] = fact_id
                data["metadata"]["taint_timestamp"] = now
            if meta_col:
                if data["is_encrypted"]:
                    enc = get_default_encrypter()
                    payload = enc.encrypt_json(data["metadata"], tenant_id=tenant_id)
                elif data["is_json"]:
                    payload = json.dumps(data["metadata"])
                else:
                    payload = data.get("raw_meta") or data.get("raw_metadata") or ""
                if has_tenant:
                    fact_updates.append((new_conf, payload, current_id, tenant_id))
                else:
                    fact_updates.append((new_conf, payload, current_id))
            else:
                if has_tenant:
                    fact_updates.append((new_conf, current_id, tenant_id))
                else:
                    fact_updates.append((new_conf, current_id))

                changes.append({
                    "fact_id": current_id,
                    "old_confidence": old_conf,
                    "new_confidence": new_conf,
                    "status": node_states[current_id].value,
                })

            for child_id in children_map.get(current_id, []):
                if child_id not in visited:
                    visited.add(child_id)
                    queue.append(child_id)

        if meta_col:
            if has_tenant:
                await self.conn.executemany(
                    f"UPDATE facts SET confidence = ?, {meta_col} = ? WHERE id = ? AND tenant_id = ?",
                    fact_updates,
                )
            else:
                await self.conn.executemany(
                    f"UPDATE facts SET confidence = ?, {meta_col} = ? WHERE id = ?",
                    fact_updates,
                )
        else:
            if has_tenant:
                await self.conn.executemany(
                    "UPDATE facts SET confidence = ? WHERE id = ? AND tenant_id = ?",
                    fact_updates,
                )
            else:
                await self.conn.executemany(
                    "UPDATE facts SET confidence = ? WHERE id = ?",
                    fact_updates,
                )

        # Record causal taint edges so downstream audits can see the provenance.
        taint_edge_params: list[tuple[Any, ...]] = []
        for change in changes:
            child_id = change["fact_id"]
            if child_id == fact_id:
                continue
            if has_tenant:
                taint_edge_params.append(
                    (
                        child_id,
                        fact_id,
                        None,
                        EDGE_TAINTED_BY,
                        None,
                        tenant_id,
                    )
                )
            else:
                taint_edge_params.append(
                    (
                        child_id,
                        fact_id,
                        None,
                        EDGE_TAINTED_BY,
                        None,
                    )
                )

        if taint_edge_params:
            if has_tenant:
                await self.conn.executemany(
                    "INSERT INTO causal_edges "
                    "(fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    taint_edge_params,
                )
            else:
                await self.conn.executemany(
                    "INSERT INTO causal_edges "
                    "(fact_id, parent_id, signal_id, edge_type, project) "
                    "VALUES (?, ?, ?, ?, ?)",
                    taint_edge_params,
                )

        await self.conn.commit()
        return TaintReport(
            source_fact_id=fact_id,
            affected_count=len(changes),
            confidence_changes=changes,
        )

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
