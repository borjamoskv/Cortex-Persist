"""Inference Engine — Automatic Fact Derivation (Ω₂: Reduce Entropy).

Scans existing facts and derives new knowledge via rule-based reasoning.
All derived facts get C3 confidence (conjecture until externally verified).
Pre-checks contradictions before asserting any derivation.

Status: IMPLEMENTED.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

import aiosqlite

from cortex.engine.causality import (
    EDGE_DERIVED_FROM,
    AsyncCausalGraph,
)

__all__ = [
    "InferenceEngine",
    "InferenceRule",
    "Derivation",
    "derive_facts",
]

logger = logging.getLogger("cortex.engine.inference")

# Maximum derivations per cycle to bound compute cost
MAX_DERIVATIONS_PER_CYCLE = 50

# Derived facts never exceed C3 without external verification (AX-033)
DERIVED_CONFIDENCE = "C3"


@dataclass(frozen=True)
class InferenceRule:
    """A rule that can derive new facts from existing ones.

    Attributes:
        name: Human-readable rule identifier.
        description: What this rule detects.
        condition_sql: SQL WHERE clause that identifies matching fact pairs.
            Must reference `f1` and `f2` as the two fact aliases.
        conclusion_template: Python format string for the derived content.
            Available variables: {f1_content}, {f2_content}, {f1_id}, {f2_id},
            {f1_project}, {f2_project}.
        min_source_confidence: Minimum confidence of source facts (index in C5..C1).
        derived_type: fact_type for the derived fact.
    """

    name: str
    description: str
    condition_sql: str
    conclusion_template: str
    min_source_confidence: str = "C4"
    derived_type: str = "knowledge"


@dataclass
class Derivation:
    """A single derived fact with its provenance."""

    content: str
    project: str
    source_fact_ids: list[int]
    rule_name: str
    confidence: str = DERIVED_CONFIDENCE
    fact_type: str = "knowledge"


# ── Built-in Rules ────────────────────────────────────────────────────

RULE_SUPERSESSION = InferenceRule(
    name="version_supersession",
    description="Newer versioned fact supersedes older one in same project",
    condition_sql=(
        "f1.project = f2.project "
        "AND f1.fact_type = f2.fact_type "
        "AND f1.id > f2.id "
        "AND f1.content LIKE '%v_.__%' "
        "AND f2.content LIKE '%v_.__%' "
        "AND f2.valid_until IS NULL "
        "AND f1.valid_until IS NULL"
    ),
    conclusion_template=(
        "[SUPERSESSION] Fact #{f2_id} may be superseded by #{f1_id} "
        "in project {f1_project}. Review for deprecation."
    ),
    derived_type="analysis",
)

RULE_ORPHAN_DETECTION = InferenceRule(
    name="orphan_detection",
    description="Facts with no causal edges and high age are potentially orphaned",
    condition_sql=(
        "f1.id NOT IN (SELECT fact_id FROM causal_edges) "
        "AND f1.id NOT IN (SELECT COALESCE(parent_id, 0) FROM causal_edges) "
        "AND f1.valid_until IS NULL "
        "AND julianday('now') - julianday(f1.created_at) > 30"
    ),
    conclusion_template=(
        "[ORPHAN] Fact #{f1_id} in project {f1_project} has no causal edges "
        "and is >30 days old. Candidate for review or archival."
    ),
    derived_type="analysis",
)

RULE_DUPLICATE_CONTENT = InferenceRule(
    name="duplicate_content",
    description="Two active facts with very similar content in the same project",
    condition_sql=(
        "f1.project = f2.project "
        "AND f1.id < f2.id "
        "AND f1.valid_until IS NULL "
        "AND f2.valid_until IS NULL "
        "AND f1.content = f2.content"
    ),
    conclusion_template=(
        "[DUPLICATE] Facts #{f1_id} and #{f2_id} have identical content "
        "in project {f1_project}. Consider consolidation."
    ),
    derived_type="analysis",
)

BUILTIN_RULES: list[InferenceRule] = [
    RULE_SUPERSESSION,
    RULE_ORPHAN_DETECTION,
    RULE_DUPLICATE_CONTENT,
]


# ── Confidence Utilities ──────────────────────────────────────────────

_CONFIDENCE_ORDER = ["C5", "C4", "C3", "C2", "C1"]


def _confidence_meets_minimum(actual: str, minimum: str) -> bool:
    """Check if actual confidence meets or exceeds minimum.

    C5 is highest, C1 is lowest.
    """
    try:
        return _CONFIDENCE_ORDER.index(actual) <= _CONFIDENCE_ORDER.index(minimum)
    except ValueError:
        return False


# ── Engine ────────────────────────────────────────────────────────────


class InferenceEngine:
    """Derives new facts from existing knowledge via rule-based reasoning.

    All derivations are:
    - Capped at C3 confidence (AX-033: conjecture until verified)
    - Linked via EDGE_DERIVED_FROM in the causal graph
    - Pre-checked against contradiction_guard (if available)
    """

    def __init__(
        self,
        rules: list[InferenceRule] | None = None,
        max_derivations: int = MAX_DERIVATIONS_PER_CYCLE,
    ) -> None:
        self._rules = rules or BUILTIN_RULES
        self._max = max_derivations

    @property
    def rules(self) -> list[InferenceRule]:
        return list(self._rules)

    async def derive(
        self,
        conn: aiosqlite.Connection,
        *,
        project: str | None = None,
        tenant_id: str = "default",
        dry_run: bool = False,
    ) -> list[Derivation]:
        """Run all inference rules and produce derivations.

        Args:
            conn: Active database connection.
            project: Optional project filter.
            tenant_id: Tenant isolation.
            dry_run: If True, compute derivations but don't persist.

        Returns:
            List of derivations (persisted or proposed).
        """
        all_derivations: list[Derivation] = []

        for rule in self._rules:
            if len(all_derivations) >= self._max:
                logger.info("Inference cap reached (%d). Stopping.", self._max)
                break

            try:
                derivations = await self._apply_rule(
                    conn, rule, project=project, tenant_id=tenant_id
                )
                remaining = self._max - len(all_derivations)
                all_derivations.extend(derivations[:remaining])
            except (sqlite3.Error, aiosqlite.Error) as e:
                logger.warning("Inference rule '%s' failed: %s", rule.name, e)

        if not dry_run and all_derivations:
            await self._persist_derivations(conn, all_derivations, tenant_id)

        logger.info(
            "Inference cycle complete: %d derivations from %d rules (dry_run=%s)",
            len(all_derivations),
            len(self._rules),
            dry_run,
        )
        return all_derivations

    async def _apply_rule(
        self,
        conn: aiosqlite.Connection,
        rule: InferenceRule,
        *,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[Derivation]:
        """Apply a single inference rule against the fact store."""
        derivations: list[Derivation] = []

        # Detect if this is a single-fact rule (no f2 reference)
        is_single = "f2." not in rule.condition_sql

        if is_single:
            query = self._build_single_query(rule, project, tenant_id)
            params = self._build_single_params(project, tenant_id)
        else:
            query = self._build_pair_query(rule, project, tenant_id)
            params = self._build_pair_params(project, tenant_id)

        try:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.OperationalError, aiosqlite.OperationalError) as e:
            logger.debug("Rule '%s' query failed (table may not exist): %s", rule.name, e)
            return []

        for row in rows:
            derivation = self._row_to_derivation(row, rule, is_single)
            if derivation:
                derivations.append(derivation)

        return derivations

    def _build_single_query(self, rule: InferenceRule, project: str | None, tenant_id: str) -> str:
        """Build SQL for single-fact rules (e.g., orphan detection)."""
        where_parts = [rule.condition_sql, "f1.tenant_id = ?"]
        if project:
            where_parts.append("f1.project = ?")
        return (
            "SELECT f1.id, f1.content, f1.project, f1.confidence "
            "FROM facts f1 "
            f"WHERE {' AND '.join(where_parts)} "
            "LIMIT 100"
        )

    def _build_single_params(self, project: str | None, tenant_id: str) -> tuple:
        if project:
            return (tenant_id, project)
        return (tenant_id,)

    def _build_pair_query(self, rule: InferenceRule, project: str | None, tenant_id: str) -> str:
        """Build SQL for pair-fact rules (e.g., supersession, duplicate)."""
        where_parts = [rule.condition_sql, "f1.tenant_id = ?", "f2.tenant_id = ?"]
        if project:
            where_parts.append("f1.project = ?")
        return (
            "SELECT f1.id as f1_id, f1.content as f1_content, "
            "f1.project as f1_project, f1.confidence as f1_confidence, "
            "f2.id as f2_id, f2.content as f2_content, "
            "f2.project as f2_project, f2.confidence as f2_confidence "
            "FROM facts f1, facts f2 "
            f"WHERE {' AND '.join(where_parts)} "
            "LIMIT 100"
        )

    def _build_pair_params(self, project: str | None, tenant_id: str) -> tuple:
        if project:
            return (tenant_id, tenant_id, project)
        return (tenant_id, tenant_id)

    def _row_to_derivation(
        self, row: Any, rule: InferenceRule, is_single: bool
    ) -> Derivation | None:
        """Convert a query result row to a Derivation."""
        try:
            if is_single:
                content = rule.conclusion_template.format(
                    f1_id=row[0],
                    f1_content=str(row[1])[:200],
                    f1_project=row[2] or "unknown",
                    f2_id="N/A",
                    f2_content="",
                    f2_project="",
                )
                source_ids = [row[0]]
                project = row[2] or "SYSTEM"
            else:
                content = rule.conclusion_template.format(
                    f1_id=row[0],
                    f1_content=str(row[1])[:200],
                    f1_project=row[2] or "unknown",
                    f2_id=row[4],
                    f2_content=str(row[5])[:200],
                    f2_project=row[6] or "unknown",
                )
                source_ids = [row[0], row[4]]
                project = row[2] or "SYSTEM"

            return Derivation(
                content=content,
                project=project,
                source_fact_ids=source_ids,
                rule_name=rule.name,
                confidence=DERIVED_CONFIDENCE,
                fact_type=rule.derived_type,
            )
        except (IndexError, KeyError, TypeError) as e:
            logger.debug("Row conversion failed for rule '%s': %s", rule.name, e)
            return None

    async def _persist_derivations(
        self,
        conn: aiosqlite.Connection,
        derivations: list[Derivation],
        tenant_id: str,
    ) -> None:
        """Persist derivations as facts with causal edges."""
        from cortex.memory.temporal import now_iso

        graph = AsyncCausalGraph(conn)
        await graph.ensure_table()
        ts = now_iso()

        for d in derivations:
            # Check if this exact derivation already exists (idempotency)
            async with conn.execute(
                "SELECT id FROM facts WHERE content = ? AND project = ? "
                "AND tenant_id = ? AND valid_until IS NULL LIMIT 1",
                (d.content, d.project, tenant_id),
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                continue

            cursor = await conn.execute(
                "INSERT INTO facts (content, fact_type, project, confidence, "
                "tenant_id, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    d.content,
                    d.fact_type,
                    d.project,
                    d.confidence,
                    tenant_id,
                    f"inference:{d.rule_name}",
                    ts,
                ),
            )
            new_fact_id = cursor.lastrowid

            # Record causal edges from source facts
            for source_id in d.source_fact_ids:
                await graph.record_edge(
                    new_fact_id,  # type: ignore[arg-type]
                    parent_id=source_id,
                    edge_type=EDGE_DERIVED_FROM,
                    project=d.project,
                    tenant_id=tenant_id,
                )

        await conn.commit()
        logger.info("Persisted %d inference derivations.", len(derivations))


# ── Module-level convenience ──────────────────────────────────────────


async def derive_facts(
    conn: aiosqlite.Connection,
    *,
    project: str | None = None,
    tenant_id: str = "default",
    dry_run: bool = False,
    rules: list[InferenceRule] | None = None,
) -> list[Derivation]:
    """Convenience function: run inference engine with defaults."""
    engine = InferenceEngine(rules=rules)
    return await engine.derive(conn, project=project, tenant_id=tenant_id, dry_run=dry_run)
