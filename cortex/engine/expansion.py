"""
CORTEX V7 — Expansion Engine (Structural Plasticity).

Manages fact consolidation and autonomous pattern promotion (Bridges -> Global Axioms).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.engine.gradient import GRADIENT, GradientType
from cortex.engine.mutation_engine import MUTATION_ENGINE
from cortex.guards.exergy_guard import calculate_exergy  # Ω₂ Injector

logger = logging.getLogger("cortex.expansion")

# Threshold for bridge promotion (Expansion Coefficient level)
_PROMOTION_THRESHOLD = 0.8
# Minimum project count for bridge promotion
_MIN_PROJECT_SUPPORT = 3


class ExpansionEngine:
    """Orchestrates structural evolution based on gradient feedback."""

    async def structural_pruning(self, conn: aiosqlite.Connection, storer: Any = None) -> int:
        """Consolidates facts and promotes bridges based on expansion levels."""
        growth = GRADIENT.get_level(GradientType.EXPANSION_COEFFICIENT)
        if growth < 0.5:
            logger.debug(
                "🌱 [EXPANSION] Low expansion coefficient (%.2f). Pruning skipped.", growth
            )
            return 0

        logger.info("🧠 [EXPANSION] Structural Phase Active (Expansion: %.2f)", growth)

        consolidated = await self._consolidate_redundant_facts(conn)
        promoted = await self._promote_successful_bridges(conn, storer)

        return consolidated + promoted

    async def _consolidate_redundant_facts(self, conn: aiosqlite.Connection) -> int:
        """
        Merges redundant 'tentative' facts with high semantic similarity.
        (Heuristic: same project, same type, overlapping content).
        """
        cursor = await conn.execute(
            "SELECT project, content, COUNT(*) as cnt "
            "FROM facts WHERE fact_type = 'bridge' AND valid_until IS NULL "
            "GROUP BY project, content HAVING cnt > 1"
        )
        dupes = await cursor.fetchall()

        count = 0
        for project, content, cnt in dupes:
            logger.info("🔗 [EXPANSION] Consolidating %d duplicate bridges in %s", cnt, project)
            inner_cursor = await conn.execute(
                "SELECT id FROM facts WHERE project = ? AND content = ? "
                "AND fact_type = 'bridge' AND valid_until IS NULL ORDER BY id ASC",
                (project, content),
            )
            rows = await inner_cursor.fetchall()
            master_id = rows[0][0]  # type: ignore[reportIndexIssue]
            to_deprecate = [r[0] for r in rows[1:]]  # type: ignore[reportIndexIssue]

            for fid in to_deprecate:
                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=fid,
                    tenant_id="system",
                    event_type="deprecate",
                    payload={"reason": f"consolidated_into_{master_id}"},
                    signer="NeuralGrowthEngine",
                    commit=False,
                )
                count += 1
        return count

    async def _promote_successful_bridges(
        self, conn: aiosqlite.Connection, storer: Any = None
    ) -> int:
        """Promotes successful bridges to global_axioms."""
        growth = GRADIENT.get_level(GradientType.EXPANSION_COEFFICIENT)
        if growth < _PROMOTION_THRESHOLD:
            return 0

        cursor = await conn.execute(
            "SELECT content, COUNT(DISTINCT project) as project_count "
            "FROM facts WHERE fact_type = 'bridge' AND valid_until IS NULL "
            "GROUP BY content HAVING project_count >= ?",
            (_MIN_PROJECT_SUPPORT,),
        )
        candidates = await cursor.fetchall()

        count = 0
        for content, p_count in candidates:
            # Ω₂: Exergy Validation. Reject decorative bridges from promotion.
            exergy_score = calculate_exergy(content)
            if exergy_score < 0.5:
                logger.warning(
                    "⚠️ [EXPANSION] Bridge promotion rejected: Low exergy (%.2f). '%s'...",
                    exergy_score,
                    content[:40],
                )
                continue

            logger.info(
                "🏆 [EXPANSION] Promoting bridge (Exergy: %.2f) to GLOBAL AXIOM: '%s'...",
                exergy_score,
                content[:50],
            )

            if storer and hasattr(storer, "store"):
                await storer.store(
                    content=f"GLOBAL_AXIOM: {content}",
                    fact_type="axiom",
                    project="global",
                    confidence="verified",
                    tags=["promoted", "v7_structural"],
                    meta={"source_bridge_count": p_count},
                    conn=conn,
                    commit=False,
                )
            else:
                from cortex.memory.temporal import now_iso

                ts = now_iso()
                # Ω₈: Morphic Resonance. Promoción a Axioma Global.
                # Un patrón que se repite en 3 proyectos deja de ser local.
                # Se sincroniza con la "conciencia colectiva".
                logger.info("🧬 [EXPANSION] Morphic Resonance detected: %s", content[:50])
                await conn.execute(
                    "INSERT INTO facts (tenant_id, project, content, fact_type, confidence, created_at, updated_at, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "system",
                        "global",
                        f"AXIOM_RESONANCE: {content}",
                        "axiom",
                        "verified",
                        ts,
                        ts,
                        json.dumps({"origin": "structural_promotion", "axiom": "Ω₈"}),  # type: ignore[reportUndefinedVariable]
                    ),
                )

            GRADIENT.pulse(GradientType.EXPANSION_COEFFICIENT, 0.05)
            count += 1

        return count


EXPANSION_ENGINE = ExpansionEngine()
