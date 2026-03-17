from __future__ import annotations

import json
import logging
<<<<<<< HEAD
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
=======
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
>>>>>>> origin/main

import aiosqlite

from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


<<<<<<< HEAD
class TaintStatus(str, Enum):
    """Tri-state causal taint (Ω₁₃).

    CLEAN: No contamination detected.
    SUSPECT: At least one parent is tainted or suspect.
    TAINTED: Node is explicitly invalidated or ≥50% parents are tainted.
    """

    CLEAN = "clean"
    SUSPECT = "suspect"
    TAINTED = "tainted"


class Confidence(str, Enum):
    """Ordinal confidence levels C5 (highest) -> C1 (lowest)."""

    C5 = "C5"
    C4 = "C4"
    C3 = "C3"
    C2 = "C2"
    C1 = "C1"


=======
>>>>>>> origin/main
EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"

<<<<<<< HEAD

# Performance optimization: ordered list for fast ordinal arithmetic (C1 lowest, C5 highest).
CONFIDENCE_ORDER: list[Confidence] = [
    Confidence.C1,
    Confidence.C2,
    Confidence.C3,
    Confidence.C4,
    Confidence.C5,
]

# Public alias for external systems (ordered highest-to-lowest as strings).
CONFIDENCE_LEVELS: list[str] = [c.value for c in reversed(CONFIDENCE_ORDER)]
=======
# Ordered from highest to lowest confidence — Ω₁₃ §4.
CONFIDENCE_LEVELS: list[str] = ["C5", "C4", "C3", "C2", "C1"]
>>>>>>> origin/main


def _downgrade_confidence(current: str, hops: int) -> str:
    """Downgrade confidence by *hops* levels (floor = C1).

    Unknown confidence values collapse directly to C1.
    """
    try:
<<<<<<< HEAD
        # Normalize incoming string to Confidence enum
        conf = Confidence(current)
        idx = CONFIDENCE_ORDER.index(conf)
    except (ValueError, KeyError):
        return Confidence.C1.value

    # CONFIDENCE_ORDER is [C1, C2, C3, C4, C5].
    # Downgrading means moving towards lower indices.
    new_idx = max(0, idx - hops)
    return CONFIDENCE_ORDER[new_idx].value
=======
        idx = CONFIDENCE_LEVELS.index(current)
    except ValueError:
        return "C1"
    new_idx = min(idx + hops, len(CONFIDENCE_LEVELS) - 1)
    return CONFIDENCE_LEVELS[new_idx]
>>>>>>> origin/main


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
<<<<<<< HEAD
    last_revalidated_at: str | None = None
=======
    last_revalidated_at: Optional[str] = None
>>>>>>> origin/main
    tainted: bool = False


class CausalGraph:
    def __init__(self):
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        """Retrieves a specific event by ID."""
        return self._events[event_id]

    def add_event(self, event: LedgerEvent) -> None:
        """Adds an event to the graph and updates child/parent adjacencies."""
        self._events[event.event_id] = event
        if event.event_id not in self._children:
            self._children[event.event_id] = []
        for parent_id in event.parent_ids:
            if parent_id not in self._children:
                self._children[parent_id] = []
            self._children[parent_id].append(event.event_id)

    def get_descendants(self, node_id: str) -> list[str]:
        """Returns the immediate children of a given node."""
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
<<<<<<< HEAD
    queue = deque([(refuted_event_id, 0)])
    visited = set()

    while queue:
        node_id, depth = queue.popleft()
=======
    queue = [(refuted_event_id, 0)]
    visited = set()

    while queue:
        node_id, depth = queue.pop(0)
>>>>>>> origin/main
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
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def ensure_table(self):
<<<<<<< HEAD
        """Ensure the causal_edges table exists with optimized indexes."""
=======
        """Ensure the causal_edges table exists."""
>>>>>>> origin/main
        sql = """
        CREATE TABLE IF NOT EXISTS causal_edges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id         INTEGER NOT NULL,
            parent_id       INTEGER,
            signal_id       INTEGER,
            edge_type       TEXT NOT NULL DEFAULT 'triggered_by',
            project         TEXT,
            tenant_id       TEXT NOT NULL DEFAULT 'default',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (fact_id) REFERENCES facts(id)
        );
        """
        await self.conn.execute(sql)
<<<<<<< HEAD
        # Ω₁₃ Optimization: Critical path indexes for O(log N) lookups
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_fact ON causal_edges(fact_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_parent ON causal_edges(parent_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_tenant ON causal_edges(tenant_id)"
        )

    async def record_edge(
        self,
        fact_id: int,
        parent_id: int | None = None,
        signal_id: int | None = None,
        edge_type: str = "triggered_by",
        project: str | None = None,
        tenant_id: str = "default",
    ) -> None:
        """Persist a causal edge (Ω₁₃) to the database."""
        sql = """
        INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        await self.conn.execute(
            sql, (fact_id, parent_id, signal_id, edge_type, project, tenant_id)
        )
=======
>>>>>>> origin/main

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
    ) -> TaintReport:
<<<<<<< HEAD
        """
        Propagate taint (Ω₁₃) through the causal DAG using batch processing.

        Optimized to reduce database roundtrips from O(N) to O(1) by fetching
        the entire affected subgraph and performing BFS logic in memory.
        """
        now = datetime.now(timezone.utc).isoformat()

        # 1. Fetch entire affected subgraph (descendants) using Recursion
        # SQLite's UNION with recursion is ideal for finding the reachability set.
        desc_sql = """
        WITH RECURSIVE descendants AS (
            SELECT ? as id
            UNION
            SELECT ce.fact_id
            FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.id
            WHERE ce.tenant_id = ? AND ce.edge_type != ?
        )
        SELECT id FROM descendants;
        """
        descendant_ids = set()
        async with self.conn.execute(desc_sql, (fact_id, tenant_id, EDGE_TAINTED_BY)) as cursor:
            async for row in cursor:
                descendant_ids.add(row[0])

        if not descendant_ids:
            return TaintReport(fact_id, 0, [])

        # 2. Fetch all parents for these descendants to build in-memory threshold logic
        # Handle SQLite parameter limits (default 999) via chunking
        node_ids_list = list(descendant_ids)
        edges: dict[int, list[int]] = {}  # child_id -> [parent_ids]
        all_node_ids = set(descendant_ids)
        
        # O(1) Fetch via chunked IN queries
        # SQLite's SQLITE_MAX_VARIABLE_NUMBER is typically 999 or 32766
        CHUNK_SIZE = 900 
        for i in range(0, len(node_ids_list), CHUNK_SIZE):
            chunk = node_ids_list[i:i+CHUNK_SIZE]
            placeholders = ",".join(["?"] * len(chunk))
            edge_sql = f"""
            SELECT fact_id, parent_id FROM causal_edges 
            WHERE fact_id IN ({placeholders}) AND edge_type != ? AND tenant_id = ?
            """
            async with self.conn.execute(
                edge_sql, (*chunk, EDGE_TAINTED_BY, tenant_id)
            ) as cursor:
                async for child_id, parent_id in cursor:
                    if child_id not in edges:
                        edges[child_id] = []
                    edges[child_id].append(parent_id)
                    all_node_ids.add(parent_id)

        # 3. Fetch facts (confidence, metadata) for all involved nodes in one pass
        all_nodes_list = list(all_node_ids)
        nodes_data: dict[int, dict[str, Any]] = {}
        for i in range(0, len(all_nodes_list), CHUNK_SIZE):
            chunk = all_nodes_list[i:i+CHUNK_SIZE]
            placeholders = ",".join(["?"] * len(chunk))
            fact_sql = (
                f"SELECT id, confidence, metadata FROM facts "
                f"WHERE id IN ({placeholders}) AND tenant_id = ?"
            )
            async with self.conn.execute(fact_sql, (*chunk, tenant_id)) as cursor:
                async for fid, conf, meta_json in cursor:
                    try:
                        meta = json.loads(meta_json or "{}")
                        is_json = True
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                        is_json = False
                    nodes_data[fid] = {
                        "confidence": conf or "C5",
                        "metadata": meta,
                        "is_json": is_json,
                    }

        # 4. In-memory BFS logic (Ω₁₃)
        node_states: dict[int, TaintStatus] = {fact_id: TaintStatus.TAINTED}
        # Build forward map (parent -> children) for traversal
        children_map: dict[int, list[int]] = {}
        for child, parents in edges.items():
            for p in parents:
                if p not in children_map:
                    children_map[p] = []
                children_map[p].append(child)

        queue: deque[int] = deque([fact_id])
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
                # thresholds logic (Ω₁₃ Rule)
                parents = edges.get(current_id, [])
                p_states = []
                for pid in parents:
                    if pid in node_states:
                        p_states.append(node_states[pid])
                    else:
                        p_meta = nodes_data.get(pid, {}).get("metadata", {})
                        p_status_val = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                        try:
                            p_states.append(TaintStatus(p_status_val))
                        except ValueError:
                            p_states.append(TaintStatus.CLEAN)

                tainted_count = p_states.count(TaintStatus.TAINTED)
                suspect_count = p_states.count(TaintStatus.SUSPECT)
                total_parents = len(parents)

                if total_parents > 0 and (tainted_count / total_parents) >= 0.5:
                    node_states[current_id] = TaintStatus.TAINTED
                    hops = 2
                elif tainted_count > 0 or suspect_count > 0:
                    node_states[current_id] = TaintStatus.SUSPECT
                    hops = 1
                else:
                    node_states[current_id] = TaintStatus.CLEAN
                    hops = 0

                new_conf = _downgrade_confidence(old_conf, hops)

                # Cascade floor: A node cannot be more confident than its least certain parent
                p_confs = [nodes_data.get(pid, {}).get("confidence", "C5") for pid in parents]
                if p_confs and hops > 0:
                    try:
                        p_indices = [CONFIDENCE_ORDER.index(Confidence(p)) for p in p_confs]
                        min_p_idx = min(p_indices)
                        new_idx = CONFIDENCE_ORDER.index(Confidence(new_conf))
                        if new_idx > min_p_idx:
                            new_conf = CONFIDENCE_ORDER[min_p_idx].value
                    except (ValueError, KeyError, IndexError):
                        pass

            # Update nodes_data for subsequent children processing
            data["confidence"] = new_conf

            # Record changes for update pass
            if data["is_json"]:
                data["metadata"]["taint_status"] = node_states[current_id].value
                data["metadata"]["tainted_by"] = fact_id
                data["metadata"]["taint_timestamp"] = now
                fact_updates.append(
                    (new_conf, json.dumps(data["metadata"]), current_id, tenant_id, True)
                )
            else:
                # Metadata is likely encrypted/opaque; only update confidence
                fact_updates.append((new_conf, current_id, tenant_id, False))

            if new_conf != old_conf:
=======
        """Propagate taint to all descendants in the causal DAG.

        Each descendant's confidence is downgraded by its hop
        distance from the source (Ω₁₃ taint propagation).
        Returns a frozen `TaintReport`.
        """
        project = "unknown"
        try:
            async with self.conn.execute(
                "SELECT project FROM facts WHERE id = ?",
                (fact_id,),
            ) as cur:
                row = await cur.fetchone()
                if row and row[0]:
                    project = row[0]
        except Exception:  # noqa: BLE001
            pass

        changes: list[dict[str, Any]] = []
        queue: list[tuple[int, int]] = [(fact_id, 0)]
        visited: set[int] = {fact_id}
        now = datetime.now(timezone.utc).isoformat()

        while queue:
            current_id, depth = queue.pop(0)

            if depth > 0:
                # Read current confidence
                old_conf = "C5"
                old_meta: dict[str, Any] = {}
                async with self.conn.execute(
                    "SELECT confidence, metadata FROM facts WHERE id = ?",
                    (current_id,),
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        old_conf = row[0] or "C5"
                        try:
                            old_meta = json.loads(row[1] or "{}")
                        except (json.JSONDecodeError, TypeError):
                            old_meta = {}

                new_conf = _downgrade_confidence(old_conf, depth)
                old_meta["tainted_by"] = fact_id
                old_meta["taint_timestamp"] = now

                await self.conn.execute(
                    "UPDATE facts SET confidence = ?, metadata = ? WHERE id = ?",
                    (new_conf, json.dumps(old_meta), current_id),
                )

                # Record taint edge
                try:
                    await self.conn.execute(
                        "INSERT INTO causal_edges "
                        "(fact_id, parent_id, edge_type, "
                        "project, tenant_id) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            current_id,
                            fact_id,
                            EDGE_TAINTED_BY,
                            project,
                            tenant_id,
                        ),
                    )
                except aiosqlite.Error as e:
                    logger.debug(
                        "Failed to record taint link: %s",
                        e,
                    )

>>>>>>> origin/main
                changes.append(
                    {
                        "fact_id": current_id,
                        "old_confidence": old_conf,
                        "new_confidence": new_conf,
<<<<<<< HEAD
                        "status": node_states[current_id].value,
                    }
                )

            # Propagate to children
            for child in children_map.get(current_id, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)

        # 5. Atomic batch updates pass (AX-020 Performance)
        # Split into JSON-meta and Opaque-meta batches for efficient executemany
        json_batch = [up[:-1] for up in fact_updates if up[-1]]
        opaque_batch = [up[:-1] for up in fact_updates if not up[-1]]

        if json_batch:
            await self.conn.executemany(
                "UPDATE facts SET confidence = ?, metadata = ? "
                "WHERE id = ? AND tenant_id = ?",
                json_batch,
            )
        if opaque_batch:
            await self.conn.executemany(
                "UPDATE facts SET confidence = ? WHERE id = ? AND tenant_id = ?",
                opaque_batch,
            )

        await self.conn.commit()
=======
                        "hops": depth,
                    },
                )

            # Traverse structural edges only
            async with self.conn.execute(
                "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND edge_type != ?",
                (current_id, EDGE_TAINTED_BY),
            ) as cursor:
                async for row in cursor:
                    child_id: int = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append((child_id, depth + 1))

>>>>>>> origin/main
        return TaintReport(
            source_fact_id=fact_id,
            affected_count=len(changes),
            confidence_changes=changes,
        )

    async def calculate_blast_radius(self, fact_id: int, tenant_id: str) -> int:
<<<<<<< HEAD
        """Calculate the number of dependent facts in the causal DAG using Ω₁₃ Recursive CTE."""
        sql = """
        WITH RECURSIVE descendants AS (
            SELECT fact_id FROM causal_edges 
            WHERE parent_id = ? AND tenant_id = ?
            UNION
            SELECT ce.fact_id FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.fact_id
            WHERE ce.tenant_id = ?
        )
        SELECT COUNT(DISTINCT fact_id) FROM descendants;
        """
        async with self.conn.execute(sql, (fact_id, tenant_id, tenant_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
=======
        """Calculate the number of dependent facts in the causal DAG."""
        count: int = 0
        queue: list[int] = [fact_id]
        visited: set[int] = {fact_id}

        while queue:
            current_id = queue.pop(0)
            async with self.conn.execute(
                "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND tenant_id = ?",
                (current_id, tenant_id),
            ) as cursor:
                async for row in cursor:
                    child_id = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append(child_id)
                        count += 1
        return count
>>>>>>> origin/main


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
<<<<<<< HEAD
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        """Finds the most recent unconsumed causal signal."""
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(tenant_id=tenant_id, project=project, limit=5)
=======
        conn: aiosqlite.Connection, project: Optional[str] = None
    ) -> Optional[int]:
        """Finds the most recent unconsumed causal signal."""
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(project=project, limit=5)
>>>>>>> origin/main
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except Exception as e:
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
<<<<<<< HEAD
    def find_parent_signal(
        db_path: str,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        """Finds the most recent unconsumed causal signal."""
        from cortex.database.core import connect

        try:
            with connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(tenant_id=tenant_id, project=project, limit=5)
=======
    def find_parent_signal(db_path: str, project: Optional[str] = None) -> Optional[int]:
        """Finds the most recent unconsumed causal signal."""
        import sqlite3

        try:
            with sqlite3.connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(project=project, limit=5)
>>>>>>> origin/main
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:
            logger.debug("Sync causal lookup failed: %s", e)
        return None


<<<<<<< HEAD
def link_causality(meta: dict[str, Any] | None, signal_id: int | None) -> dict[str, Any]:
=======
def link_causality(meta: Optional[dict[str, Any]], signal_id: Optional[int]) -> dict[str, Any]:
>>>>>>> origin/main
    """Attaches causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m
