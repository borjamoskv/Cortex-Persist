from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import aiosqlite

from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"

# Ordered from highest to lowest confidence — Ω₁₃ §4.
CONFIDENCE_LEVELS: list[str] = ["C5", "C4", "C3", "C2", "C1"]


def _downgrade_confidence(current: str, hops: int) -> str:
    """Downgrade confidence by *hops* levels (floor = C1).

    Unknown confidence values collapse directly to C1.
    """
    try:
        idx = CONFIDENCE_LEVELS.index(current)
    except ValueError:
        return "C1"
    new_idx = min(idx + hops, len(CONFIDENCE_LEVELS) - 1)
    return CONFIDENCE_LEVELS[new_idx]


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
    queue = [(refuted_event_id, 0)]
    visited = set()

    while queue:
        node_id, depth = queue.pop(0)
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
        """Ensure the causal_edges table exists."""
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

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
    ) -> TaintReport:
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
                    "SELECT confidence, meta FROM facts WHERE id = ?",
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
                    "UPDATE facts SET confidence = ?, meta = ? "
                    "WHERE id = ?",
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
                        "Failed to record taint link: %s", e,
                    )

                changes.append(
                    {
                        "fact_id": current_id,
                        "old_confidence": old_conf,
                        "new_confidence": new_conf,
                        "hops": depth,
                    },
                )

            # Traverse structural edges only
            async with self.conn.execute(
                "SELECT fact_id FROM causal_edges "
                "WHERE parent_id = ? AND edge_type != ?",
                (current_id, EDGE_TAINTED_BY),
            ) as cursor:
                async for row in cursor:
                    child_id: int = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append((child_id, depth + 1))

        return TaintReport(
            source_fact_id=fact_id,
            affected_count=len(changes),
            confidence_changes=changes,
        )

    async def calculate_blast_radius(self, fact_id: int, tenant_id: str) -> int:
        """Calculate the number of dependent facts in the causal DAG."""
        count: int = 0
        queue: list[int] = [fact_id]
        visited: set[int] = {fact_id}

        while queue:
            current_id = queue.pop(0)
            async with self.conn.execute(
                "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND tenant_id = ?",
                (current_id, tenant_id)
            ) as cursor:
                async for row in cursor:
                    child_id = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append(child_id)
                        count += 1
        return count


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
        conn: aiosqlite.Connection, project: Optional[str] = None
    ) -> Optional[int]:
        """Finds the most recent unconsumed causal signal."""
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(project=project, limit=5)
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except Exception as e:
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
    def find_parent_signal(
        db_path: str, project: Optional[str] = None
    ) -> Optional[int]:
        """Finds the most recent unconsumed causal signal."""
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:
            logger.debug("Sync causal lookup failed: %s", e)
        return None


def link_causality(meta: Optional[dict[str, Any]], signal_id: Optional[int]) -> dict[str, Any]:
    """Attaches causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m
