"""Metastability Probe — Detect Fragile Stability (Ω₁₃).

Identifies facts/subsystems that appear stable only because nothing
has perturbed them. Absence of failure is not proof of robustness.

Ω₁₃ §15.8: metastability_probe_required_before_declaring_stability = true
             anomaly_detection_alone_is_insufficient = true

Status: IMPLEMENTED (upgraded from PARTIAL).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiosqlite

__all__ = [
    "MetastabilityReport",
    "probe_metastability",
    "probe_untested_assumptions",
]

logger = logging.getLogger("cortex.immune.probe")


@dataclass
class MetastabilityReport:
    """Result of a metastability probe.

    Attributes:
        total_probed: Number of facts evaluated.
        metastable_count: Facts identified as metastable (fragile green).
        metastable_facts: Details of each metastable fact.
        untested_assumptions: High-confidence facts with no verification events.
    """

    total_probed: int = 0
    metastable_count: int = 0
    metastable_facts: list[dict[str, Any]] = field(default_factory=list)
    untested_assumptions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def fragility_ratio(self) -> float:
        """Fraction of probed facts that are metastable."""
        if self.total_probed == 0:
            return 0.0
        return self.metastable_count / self.total_probed


async def probe_metastability(
    conn: aiosqlite.Connection,
    *,
    project: str | None = None,
    tenant_id: str = "default",
    min_age_days: int = 30,
    limit: int = 200,
) -> MetastabilityReport:
    """Probe for metastable facts — structurally unchallenged knowledge.

    A fact is metastable if:
    1. No downstream causal edges (nothing depends on it)
    2. Age > min_age_days (old enough that absence of use is meaningful)
    3. Still active (valid_until IS NULL)

    These facts appear "green" in dashboards but are fragile —
    they've never been tested, relied upon, or challenged.

    Args:
        conn: Active database connection.
        project: Optional project filter.
        tenant_id: Tenant isolation.
        min_age_days: Minimum age in days to consider.
        limit: Maximum facts to probe.

    Returns:
        MetastabilityReport with findings.
    """
    report = MetastabilityReport()

    # Find facts with no downstream edges and sufficient age
    query = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.created_at,
               julianday('now') - julianday(f.created_at) as age_days
        FROM facts f
        WHERE f.valid_until IS NULL
          AND f.tenant_id = ?
          AND julianday('now') - julianday(f.created_at) > ?
          AND f.id NOT IN (
              SELECT DISTINCT parent_id FROM causal_edges
              WHERE parent_id IS NOT NULL AND tenant_id = ?
          )
    """
    params: list[Any] = [tenant_id, min_age_days, tenant_id]

    if project:
        query += " AND f.project = ?"
        params.append(project)

    query += " ORDER BY age_days DESC LIMIT ?"
    params.append(limit)

    try:
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
    except Exception as e:
        logger.warning("Metastability probe query failed: %s", e)
        return report

    report.total_probed = len(rows)

    for row in rows:
        fact_id, content, proj, fact_type, confidence, _, age_days = row

        # Calculate fragility score: older + more isolated = more fragile
        # Also check if fact has NO upstream edges either (true orphan)
        try:
            async with conn.execute(
                "SELECT COUNT(*) FROM causal_edges WHERE fact_id = ? AND tenant_id = ?",
                (fact_id, tenant_id),
            ) as cursor:
                edge_row = await cursor.fetchone()
                upstream_edges = edge_row[0] if edge_row else 0
        except Exception:
            upstream_edges = 0

        fragility = age_days / max(upstream_edges + 1, 1)

        # Threshold: facts with high fragility are metastable
        if fragility > min_age_days:
            report.metastable_count += 1
            report.metastable_facts.append(
                {
                    "fact_id": fact_id,
                    "content": (content or "")[:200],
                    "project": proj,
                    "fact_type": fact_type,
                    "confidence": confidence,
                    "age_days": round(age_days, 1),
                    "upstream_edges": upstream_edges,
                    "fragility_score": round(fragility, 2),
                }
            )

    logger.info(
        "Metastability probe: %d/%d facts are metastable (fragility ratio: %.1f%%)",
        report.metastable_count,
        report.total_probed,
        report.fragility_ratio * 100,
    )
    return report


async def probe_untested_assumptions(
    conn: aiosqlite.Connection,
    *,
    tenant_id: str = "default",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find high-confidence facts with no linked verification events.

    C4/C5-Static facts that have never been confirmed by a test,
    external check, or runtime validation are untested assumptions.

    Returns:
        List of fact dicts with confidence and age information.
    """
    query = """
        SELECT f.id, f.content, f.project, f.confidence, f.created_at,
               julianday('now') - julianday(f.created_at) as age_days
        FROM facts f
        WHERE f.valid_until IS NULL
          AND f.tenant_id = ?
          AND f.confidence IN ('C4', 'C5')
          AND f.id NOT IN (
              SELECT DISTINCT fact_id FROM causal_edges
              WHERE edge_type IN ('verified_by', 'tested_by', 'confirmed_by')
              AND tenant_id = ?
          )
        ORDER BY age_days DESC
        LIMIT ?
    """

    results: list[dict[str, Any]] = []
    try:
        async with conn.execute(query, (tenant_id, tenant_id, limit)) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            results.append(
                {
                    "fact_id": row[0],
                    "content": (row[1] or "")[:200],
                    "project": row[2],
                    "confidence": row[3],
                    "age_days": round(row[5], 1) if row[5] else 0,
                    "status": "UNTESTED_ASSUMPTION",
                }
            )

    except Exception as e:
        logger.warning("Untested assumptions probe failed: %s", e)

    return results
