"""
CORTEX V7 — Neural Growth Engine (Synaptic Plasticity).

Manages fact consolidation and autonomous pattern promotion (Bridges -> Global Axioms).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.mutation_engine import MUTATION_ENGINE

logger = logging.getLogger("cortex.growth")

# Threshold for bridge promotion (Neural-Growth level)
_PROMOTION_THRESHOLD = 0.8
# Minimum project count for bridge promotion
_MIN_PROJECT_SUPPORT = 3


class NeuralGrowthEngine:
    """Orchestrates structural evolution based on hormonal feedback."""

    async def synaptic_pruning(self, conn: aiosqlite.Connection, storer: Any = None) -> int:
        """Consolidates facts and promotes bridges based on growth levels."""
        growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
        if growth < 0.5:
            logger.debug("🌱 [GROWTH] Low growth (%.2f). Pruning skipped.", growth)
            return 0

        logger.info("🧠 [GROWTH] Synaptic Phase Active (Growth: %.2f)", growth)

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
            logger.info("🔗 [GROWTH] Consolidating %d duplicate bridges in %s", cnt, project)
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
        growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
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
            logger.info(
                "🏆 [GROWTH] Promoting bridge to GLOBAL AXIOM: '%s' (%d projects)",
                content[:50],
                p_count,
            )

            if storer and hasattr(storer, "store"):
                await storer.store(
                    content=f"GLOBAL_AXIOM: {content}",
                    fact_type="axiom",
                    project="global",
                    confidence="verified",
                    tags=["promoted", "v7_synaptic"],
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
                logger.info("🧬 [GROWTH] Morphic Resonance detected: %s", content[:50])
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
                        json.dumps({"origin": "synaptic_promotion", "axiom": "Ω₈"}),  # type: ignore[reportUndefinedVariable]
                    ),
                )

            ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.05)
            count += 1

        return count


GROWTH_ENGINE = NeuralGrowthEngine()
