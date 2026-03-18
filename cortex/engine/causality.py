from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import aiosqlite

from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


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


CONFIDENCE_LEVELS = ["C1", "C2", "C3", "C4", "C5"]


EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"

# Performance optimization: ordered list for fast ordinal arithmetic.
CONFIDENCE_ORDER: list[Confidence] = [
    Confidence.C1,
    Confidence.C2,
    Confidence.C3,
    Confidence.C4,
    Confidence.C5,
]

# Public alias: ordered highest-to-lowest as string values.
CONFIDENCE_LEVELS: list[str] = ["C5", "C4", "C3", "C2", "C1"]


def _downgrade_confidence(current: str, hops: int) -> str:
    """Downgrade confidence by *hops* levels (floor = C1).

    Unknown confidence values collapse directly to C1.
    """
    try:
        # Normalize incoming string to Confidence enum
        conf = Confidence(current)
        idx = CONFIDENCE_ORDER.index(conf)
    except (ValueError, KeyError):
        return Confidence.C1.value

    # CONFIDENCE_ORDER is [C1, C2, C3, C4, C5].
    # Downgrading means moving towards lower indices.
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
    last_revalidated_at: str | None = None
    tainted: bool = False
    peer_attestations: list[str] = field(default_factory=list)

    def add_attestation(self, tx_id: str, trust_boost: float = 0.1) -> None:
        """Dynamically increase trust score based on peer attestations."""
        if tx_id not in self.peer_attestations:
            self.peer_attestations.append(tx_id)
            self.trust_score = min(1.0, self.trust_score + trust_boost)


def hash_event(event: LedgerEvent) -> str:
    """Generate an Arweave-compatible Base64URL(SHA-256) hash of the event."""
    data = {
        "parent_ids": sorted(event.parent_ids),
        "status": event.status.value if isinstance(event.status, Enum) else event.status,
        "trust_score": event.trust_score,
        "created_at": event.created_at,
        "tainted": event.tainted,
        "peer_attestations": sorted(event.peer_attestations),
    }
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


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
        """Propagate taint (Ω₁₃) through the causal DAG.

        Algorithm:
        1. BFS from `fact_id` (the source of contamination).
        2. Source is marked TAINTED.
        3. Children are marked SUSPECT if not already TAINTED.
        4. If child has ≥50% TAINTED parents, it escalates to TAINTED.
        5. confidence is downgraded: TAINTED=-2, SUSPECT=-1.
        """
        now = datetime.now(timezone.utc).isoformat()
        changes: list[dict[str, Any]] = []
        queue: list[int] = [fact_id]

        # In-memory session state for this propagation run
        node_states: dict[int, TaintStatus] = {fact_id: TaintStatus.TAINTED}
        visited: set[int] = {fact_id}

        while queue:
            current_id = queue.pop(0)

            # 1. Update the fact in DB
            async with self.conn.execute(
                "SELECT confidence, metadata FROM facts WHERE id = ?", (current_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    continue
                old_conf_str = row[0] or "C5"
                try:
                    meta = json.loads(row[1] or "{}")
                except (json.JSONDecodeError, TypeError):
                    meta = {}

            # Recalculate confidence based on taint status
            # Ω₁₃: TAINTED parent -> -2 steps, SUSPECT parent -> -1 step.
            # However, for the *source* node (depth 0), we might want to force C1.
            if current_id == fact_id:
                new_conf_str = Confidence.C1.value
            else:
                # Aggregate parent states to decide this node's status and confidence
                # This is a bit expensive but necessary for Ω₁₃ integrity.
                parents_status: list[TaintStatus] = []
                async with self.conn.execute(
                    "SELECT parent_id FROM causal_edges WHERE fact_id = ? AND edge_type != ?",
                    (current_id, EDGE_TAINTED_BY),
                ) as p_cur:
                    async for p_row in p_cur:
                        p_id = p_row[0]
                        if p_id in node_states:
                            parents_status.append(node_states[p_id])
                        else:
                            # Check DB for existing taint status in metadata
                            async with self.conn.execute(
                                "SELECT metadata FROM facts WHERE id = ?", (p_id,)
                            ) as p_db_cur:
                                p_db_row = await p_db_cur.fetchone()
                                if p_db_row:
                                    p_meta = json.loads(p_db_row[0] or "{}")
                                    p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                                    parents_status.append(TaintStatus(p_status))

                parent_conf_vals: list[str] = []
                async with self.conn.execute(
                    "SELECT parent_id FROM causal_edges WHERE fact_id = ? AND edge_type != ?",
                    (current_id, EDGE_TAINTED_BY),
                ) as p_cur:
                    async for p_row in p_cur:
                        p_id = p_row[0]
                        # Fetch current parent confidence from DB (or from our current session memory if updated)
                        # To keep it simple, we query the DB since BFS ensures parents are updated before children.
                        async with self.conn.execute(
                            "SELECT confidence FROM facts WHERE id = ?", (p_id,)
                        ) as p_conf_cur:
                            p_conf_row = await p_conf_cur.fetchone()
                            if p_conf_row:
                                parent_conf_vals.append(p_conf_row[0])

                tainted_count = parents_status.count(TaintStatus.TAINTED)
                suspect_count = parents_status.count(TaintStatus.SUSPECT)
                total_parents = len(parents_status)

                if total_parents > 0 and (tainted_count / total_parents) >= 0.5:
                    node_states[current_id] = TaintStatus.TAINTED
                    hops = 2
                elif tainted_count > 0 or suspect_count > 0:
                    node_states[current_id] = TaintStatus.SUSPECT
                    hops = 1
                else:
                    node_states[current_id] = TaintStatus.CLEAN
                    hops = 0

                # Relative drop from own current level
                new_conf_str = _downgrade_confidence(old_conf_str, hops)

                # Ω₁₃: Cascade property. A node cannot be more confident than its least certain parent.
                # If we are TAINTED or SUSPECT, we must be at most as certain as our basis.
                if parent_conf_vals and hops > 0:
                    # In our Alphabetical order C1 < C2 < C3 < C4 < C5, so min() gives the lowest level.
                    min_parent_conf = min(parent_conf_vals)
                    if new_conf_str > min_parent_conf:  # e.g. "C3" > "C1"
                        new_conf_str = min_parent_conf

            # Persist changes
            meta["taint_status"] = node_states[current_id].value
            meta["tainted_by"] = fact_id
            meta["taint_timestamp"] = now

            await self.conn.execute(
                "UPDATE facts SET confidence = ?, metadata = ? WHERE id = ?",
                (new_conf_str, json.dumps(meta), current_id),
            )

            if new_conf_str != old_conf_str:
                changes.append(
                    {
                        "fact_id": current_id,
                        "old_confidence": old_conf_str,
                        "new_confidence": new_conf_str,
                        "status": node_states[current_id].value,
                    }
                )

            # 2. Add children to queue
            async with self.conn.execute(
                "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND edge_type != ?",
                (current_id, EDGE_TAINTED_BY),
            ) as cursor:
                async for row in cursor:
                    child_id = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append(child_id)

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
                (current_id, tenant_id),
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
        conn: aiosqlite.Connection, project: str | None = None
    ) -> int | None:
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
    def find_parent_signal(db_path: str, project: str | None = None) -> int | None:
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


def link_causality(meta: dict[str, Any] | None, signal_id: int | None) -> dict[str, Any]:
    """Attaches causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m
