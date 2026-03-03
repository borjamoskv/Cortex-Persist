"""Causality Engine — AX-014: Mapping the Causal Chord (Ω₁).

ANAMNESIS-Ω: The Ariadne's Thread.
Links facts to the signals that triggered them, creating
a directed acyclic graph (DAG) of consequence. Every decision
must be traceable to an axiom or business need.

EU AI Act Article 12 compliance: full decision traceability.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

from cortex.signals.bus import SignalBus

logger = logging.getLogger("cortex.causality")

__all__ = ["CausalOracle", "CausalEdge", "CausalGraph", "link_causality"]

# ── Schema ──────────────────────────────────────────────────────────

_CREATE_CAUSAL_EDGES = """\
CREATE TABLE IF NOT EXISTS causal_edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id     INTEGER NOT NULL,
    parent_id   INTEGER,
    signal_id   INTEGER,
    edge_type   TEXT NOT NULL DEFAULT 'triggered_by',
    project     TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (fact_id) REFERENCES facts(id)
);
"""

_CREATE_CAUSAL_INDEXES = """\
CREATE INDEX IF NOT EXISTS idx_causal_fact ON causal_edges(fact_id);
CREATE INDEX IF NOT EXISTS idx_causal_parent ON causal_edges(parent_id);
CREATE INDEX IF NOT EXISTS idx_causal_signal ON causal_edges(signal_id);
CREATE INDEX IF NOT EXISTS idx_causal_project ON causal_edges(project);
"""

# ── Edge Types ──────────────────────────────────────────────────────

EDGE_TRIGGERED_BY = "triggered_by"  # fact was triggered by signal
EDGE_UPDATED_FROM = "updated_from"  # fact is an update of another fact
EDGE_DEPRECATED_BY = "deprecated_by"  # fact was deprecated by another
EDGE_DERIVED_FROM = "derived_from"  # fact was derived from analysis


# ── Data Model ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CausalEdge:
    """A single edge in the causal DAG."""

    id: int
    fact_id: int
    parent_id: int | None
    signal_id: int | None
    edge_type: str
    project: str | None
    tenant_id: str
    created_at: str


def _edge_from_row(row: tuple) -> CausalEdge:
    """Convert a DB row to a CausalEdge."""
    return CausalEdge(
        id=row[0],
        fact_id=row[1],
        parent_id=row[2],
        signal_id=row[3],
        edge_type=row[4],
        project=row[5],
        tenant_id=row[6],
        created_at=row[7],
    )


# ── Causal Graph ────────────────────────────────────────────────────


class CausalGraph:
    """Persistent causal DAG backed by SQLite.

    Provides traversal and lineage queries for EU AI Act
    Article 12 compliance (full decision traceability).
    """

    __slots__ = ("_conn", "_ready")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ready = False

    def ensure_table(self) -> None:
        """Create the causal_edges table if it doesn't exist."""
        if self._ready:
            return
        self._conn.executescript(_CREATE_CAUSAL_EDGES + _CREATE_CAUSAL_INDEXES)
        self._conn.commit()
        self._ready = True

    def record_edge(
        self,
        fact_id: int,
        *,
        parent_id: int | None = None,
        signal_id: int | None = None,
        edge_type: str = EDGE_TRIGGERED_BY,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> int:
        """Record a causal edge between a fact and its origin.

        Returns the edge ID.
        """
        self.ensure_table()
        cursor = self._conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (fact_id, parent_id, signal_id, edge_type, project, tenant_id),
        )
        self._conn.commit()
        edge_id: int = cursor.lastrowid  # type: ignore[assignment]
        logger.debug(
            "Causal edge #%d: fact %d ←[%s]← parent=%s signal=%s",
            edge_id,
            fact_id,
            edge_type,
            parent_id,
            signal_id,
        )
        return edge_id

    def trace_ancestors(self, fact_id: int, max_depth: int = 50) -> list[CausalEdge]:
        """Walk the DAG upward from a fact to its root causes.

        Returns edges in order from immediate parent to oldest ancestor.
        This is the core query for EU AI Act Article 12 traceability.
        """
        self.ensure_table()
        result: list[CausalEdge] = []
        visited: set[int] = set()
        current = fact_id

        for _ in range(max_depth):
            if current in visited:
                break  # Cycle detected — halt
            visited.add(current)

            cursor = self._conn.execute(
                "SELECT id, fact_id, parent_id, signal_id, edge_type, project, tenant_id, created_at "
                "FROM causal_edges WHERE fact_id = ? ORDER BY created_at DESC LIMIT 1",
                (current,),
            )
            row = cursor.fetchone()
            if not row:
                break

            edge = _edge_from_row(row)
            result.append(edge)

            if edge.parent_id is not None:
                current = edge.parent_id
            else:
                break  # Root reached (signal-only edge)

        return result

    def trace_descendants(self, fact_id: int, max_depth: int = 50) -> list[CausalEdge]:
        """Walk the DAG downward from a fact to its consequences.

        Returns edges in BFS order.
        """
        self.ensure_table()
        result: list[CausalEdge] = []
        visited: set[int] = set()
        queue = [fact_id]

        for _ in range(max_depth):
            if not queue:
                break
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            cursor = self._conn.execute(
                "SELECT id, fact_id, parent_id, signal_id, edge_type, project, tenant_id, created_at "
                "FROM causal_edges WHERE parent_id = ? ORDER BY created_at ASC",
                (current,),
            )
            for row in cursor.fetchall():
                edge = _edge_from_row(row)
                result.append(edge)
                queue.append(edge.fact_id)

        return result

    def lineage_report(self, fact_id: int) -> dict[str, Any]:
        """Generate a compliance-ready lineage report for a fact.

        Returns a dict suitable for EU AI Act Article 12 reporting.
        """
        ancestors = self.trace_ancestors(fact_id)
        descendants = self.trace_descendants(fact_id)

        # Collect all signal IDs in the chain for cross-referencing
        all_edges = ancestors + descendants
        signal_ids = {e.signal_id for e in all_edges if e.signal_id is not None}

        return {
            "fact_id": fact_id,
            "ancestor_count": len(ancestors),
            "descendant_count": len(descendants),
            "depth": len(ancestors),
            "root_signal_ids": sorted(signal_ids),
            "ancestors": [
                {
                    "edge_id": e.id,
                    "parent_id": e.parent_id,
                    "signal_id": e.signal_id,
                    "edge_type": e.edge_type,
                    "created_at": e.created_at,
                }
                for e in ancestors
            ],
            "descendants": [
                {
                    "edge_id": e.id,
                    "fact_id": e.fact_id,
                    "edge_type": e.edge_type,
                    "created_at": e.created_at,
                }
                for e in descendants
            ],
            "compliance": {
                "eu_ai_act_article_12": len(ancestors) > 0,
                "full_traceability": all(
                    e.signal_id is not None or e.parent_id is not None for e in ancestors
                ),
            },
        }

    def stats(self) -> dict[str, Any]:
        """Aggregate causal graph statistics."""
        self.ensure_table()
        total = self._conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()
        by_type = self._conn.execute(
            "SELECT edge_type, COUNT(*) FROM causal_edges GROUP BY edge_type"
        ).fetchall()
        orphans = self._conn.execute(
            "SELECT COUNT(*) FROM causal_edges WHERE parent_id IS NULL AND signal_id IS NULL"
        ).fetchone()

        return {
            "total_edges": total[0] if total else 0,
            "by_edge_type": {r[0]: r[1] for r in by_type},
            "orphan_edges": orphans[0] if orphans else 0,
        }


# ── Oracle (Original API — preserved for backward compatibility) ────


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact."""

    @staticmethod
    def find_parent_signal(db_path: str, project: str | None = None) -> int | None:
        """Finds the most recent unconsumed causal signal.

        Looks for 'plan:done', 'task:start', or 'apotheosis:heal'
        signals from the last 60 seconds.
        """
        try:
            with sqlite3.connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except (sqlite3.Error, OSError) as e:
            logger.debug("Causal lookup failed: %s", e)
        return None

    @staticmethod
    def record_fact_causality(
        db_path: str,
        fact_id: int,
        *,
        parent_fact_id: int | None = None,
        signal_id: int | None = None,
        edge_type: str = EDGE_TRIGGERED_BY,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> int | None:
        """Record a causal edge for a newly stored fact.

        Convenience method that opens its own connection.
        """
        try:
            with sqlite3.connect(db_path) as conn:
                graph = CausalGraph(conn)
                return graph.record_edge(
                    fact_id,
                    parent_id=parent_fact_id,
                    signal_id=signal_id,
                    edge_type=edge_type,
                    project=project,
                    tenant_id=tenant_id,
                )
        except (sqlite3.Error, OSError) as e:
            logger.debug("Causal edge recording failed: %s", e)
            return None


# ── Linking Helper (preserved API) ──────────────────────────────────


def link_causality(meta: dict[str, Any] | None, signal_id: int | None) -> dict[str, Any]:
    """Attaches causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m
