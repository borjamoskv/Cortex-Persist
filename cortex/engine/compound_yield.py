"""
CHRONOS-1 Compound Yield System — Axiom Ω₁₁
Detects causal chains and projects exponential returns of sovereign agent work.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.memory.temporal import now_iso
from cortex.signals.bus import SignalBus

logger = logging.getLogger("cortex.chronos.compound")

__all__ = ["CompoundChain", "CompoundReport", "CompoundProjector", "CompoundYieldTracker"]


# ── Data Models ───────────────────────────────────────────────────────


@dataclass
class CompoundChain:
    """Represents a single compounding chain of actions in the CORTEX DAG."""

    root_fact_id: int
    depth: int
    fact_ids: set[int] = field(default_factory=set)
    linear_hours: float = 0.0
    compound_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_fact_id": self.root_fact_id,
            "depth": self.depth,
            "chain_length": len(self.fact_ids),
            "linear_hours": round(self.linear_hours, 2),
            "compound_hours": round(self.compound_hours, 2),
        }


@dataclass
class CompoundReport:
    """Result of a full CHRONOS-1 compound chain analysis."""

    chains: list[CompoundChain]
    total_linear: float
    total_compound: float
    multiplier: float
    reuse_rate: float
    project: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chains": [c.to_dict() for c in self.chains],
            "total_linear": round(self.total_linear, 2),
            "total_compound": round(self.total_compound, 2),
            "multiplier": round(self.multiplier, 2),
            "reuse_rate": self.reuse_rate,
            "project": self.project,
        }

    def summary(self) -> str:
        s = f"⏱️ CHRONOS Ω₁₁ ({self.project or 'global'}): "
        s += f"Chains: {len(self.chains)} | "
        s += f"Linear: {self.total_linear:,.1f}h | "
        s += f"Compound: {self.total_compound:,.1f}h | "
        s += f"Multiplier: {self.multiplier:.1f}x"
        return s


# ── Engine Core ───────────────────────────────────────────────────────


class CompoundProjector:
    """Axiom Ω₁₁ projection models (1yr, 5yr, 10yr)."""

    @dataclass
    class ProjectionResult:
        years: int
        total_linear: float
        total_compound: float
        multiplier: float
        yearly_linear: list[float]
        yearly_compound: list[float]

    @staticmethod
    def project(
        base_hours_per_year: float,
        reuse_rate: float = 0.15,
        years: int = 10,
    ) -> ProjectionResult:
        """Project linear vs compound yield over a given number of years.

        Assumes every year the base hours are repeated, but previous years'
        work compounds on the current year via the reuse rate.
        """
        yearly_linear = []
        yearly_compound = []

        cumulative_linear = 0.0
        cumulative_compound = 0.0

        # We model this as each year adds 'base_hours', and those base hours
        # compound over the remaining years.
        for year in range(1, years + 1):
            cumulative_linear += base_hours_per_year
            yearly_linear.append(cumulative_linear)

            # This year's work is base_hours.
            # Work from N years ago has compounded N times.
            current_yr_yield = 0.0
            for past_yr in range(year):
                # distance = year - past_yr
                # The yield of the work initially done in past_yr, right now:
                # Actually, standard compound interest: Principal * (1 + r)^n
                current_yr_yield += base_hours_per_year * ((1 + reuse_rate) ** past_yr)

            cumulative_compound += current_yr_yield
            yearly_compound.append(cumulative_compound)

        mult = cumulative_compound / cumulative_linear if cumulative_linear > 0 else 0.0

        return CompoundProjector.ProjectionResult(
            years=years,
            total_linear=round(cumulative_linear, 2),
            total_compound=round(cumulative_compound, 2),
            multiplier=round(mult, 2),
            yearly_linear=[round(x, 2) for x in yearly_linear],
            yearly_compound=[round(x, 2) for x in yearly_compound],
        )


class CompoundYieldTracker:
    """Engine module that detects causal chains and calculates Ω₁₁ yield."""

    def __init__(self, db_path: str, reuse_rate: float = 0.15) -> None:
        self.db_path = db_path
        self.reuse_rate = reuse_rate

    def _get_base_hours(self, conn: Any, fact_id: int) -> float:
        """Extract linear Hours_Saved from a fact's meta, or estimate."""
        import json

        # First check meta for explicitly tracked hours
        cursor = conn.execute("SELECT meta FROM facts WHERE id = ?", (fact_id,))
        row = cursor.fetchone()
        if not row:
            return 0.0

        try:
            meta = json.loads(row[0])
            # Check if chronos explicit report exists in meta
            if "hours_saved" in meta:
                return float(meta["hours_saved"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # If no explicit hours, assign a default baseline value of 0.5 hours
        # This prevents 0 yield for chained structural facts that lack explicit tracking
        return 0.5

    def analyze_chains(self, project: str | None = None) -> CompoundReport:
        """Detect chains in the causal DAG and calculate their compound yield."""
        try:
            with db_connect(self.db_path) as conn:
                query = """
                    SELECT parent_id, fact_id, edge_type
                    FROM causal_edges
                    WHERE parent_id IS NOT NULL
                """
                params = []
                if project:
                    query += " AND project = ?"
                    params.append(project)

                cursor = conn.execute(query, params)
                edges = cursor.fetchall()

                # 1. Build adjacency list for children (DAG)
                children: dict[int, list[int]] = {}
                all_nodes: set[int] = set()
                has_parent: set[int] = set()

                for parent, child, _ in edges:
                    if parent not in children:
                        children[parent] = []
                    children[parent].append(child)
                    all_nodes.add(parent)
                    all_nodes.add(child)
                    has_parent.add(child)

                # 2. Find internal roots (nodes with no parents in this subgraph)
                roots = all_nodes - has_parent

                # 3. For each root, trace depth and calculate compound hours
                chains: list[CompoundChain] = []
                total_linear = 0.0
                total_compound = 0.0

                # Using iterative BFS/DFS to find all paths from roots and assign max depth
                for root in roots:
                    chain = CompoundChain(root_fact_id=root, depth=0)

                    # queue stores (node, depth)
                    queue = [(root, 0)]
                    visited_in_chain: set[int] = set()

                    # Track max depth reached in this chain
                    max_depth = 0

                    while queue:
                        node, depth = queue.pop(0)

                        if node in visited_in_chain:
                            continue  # Protect against cycles
                        visited_in_chain.add(node)

                        max_depth = max(max_depth, depth)
                        chain.fact_ids.add(node)

                        # Calculate linear and compound for this node
                        base_h = self._get_base_hours(conn, node)
                        comp_h = base_h * ((1 + self.reuse_rate) ** depth)

                        chain.linear_hours += base_h
                        chain.compound_hours += comp_h

                        # Add children
                        for child in children.get(node, []):
                            queue.append((child, depth + 1))

                    chain.depth = max_depth
                    if max_depth > 0:  # Only count actual chains, not isolated nodes
                        chains.append(chain)
                        total_linear += chain.linear_hours
                        total_compound += chain.compound_hours

                # Sort chains by compound value
                chains.sort(key=lambda c: c.compound_hours, reverse=True)

                mult = total_compound / total_linear if total_linear > 0 else 0.0

                return CompoundReport(
                    chains=chains,
                    total_linear=total_linear,
                    total_compound=total_compound,
                    multiplier=mult,
                    reuse_rate=self.reuse_rate,
                    project=project,
                )

        except (sqlite3.Error, ValueError, TypeError, RuntimeError) as e:
            logger.error("Failed to analyze compound chains: %s", e)
            return CompoundReport(
                chains=[], total_linear=0, total_compound=0, multiplier=0, reuse_rate=0
            )

    def persist_report(
        self,
        report: CompoundReport,
        project: str = "system",
    ) -> int | None:
        """Persist a CHRONOS Compound report as a CORTEX fact + emit signal."""
        try:
            import json

            with db_connect(self.db_path) as conn:
                ts = now_iso()
                content = report.summary()
                meta_json = json.dumps(report.to_dict())

                cursor = conn.execute(
                    "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence,"
                    " valid_from, source, meta, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "default",
                        project,
                        content,
                        "knowledge",
                        '["chronos", "compound", "metrics"]',
                        "observed",
                        ts,
                        "chronos-compound",
                        meta_json,
                        ts,
                        ts,
                    ),
                )
                fact_id: int = cursor.lastrowid  # type: ignore[assignment]

                # Emit signal to bus
                bus = SignalBus(conn)
                bus.emit(
                    "chronos:compound_audit",
                    payload=report.to_dict(),
                    source="chronos-compound",
                    project=project,
                )

                logger.info("CHRONOS Compound report persisted as fact #%d", fact_id)
                return fact_id

        except (sqlite3.Error, ValueError, TypeError, RuntimeError) as e:
            logger.warning("CHRONOS Compound persistence failed: %s", e)
            return None
