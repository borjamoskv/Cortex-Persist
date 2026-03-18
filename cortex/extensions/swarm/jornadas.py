"""CORTEX v8.0 — Jornadas de Convivencia (Swarm Collective Synchronization).

This module implements the "Jornadas" protocol, a collective REM sleep
cycle for the Swarm. During a Jornada, individual agents pause their normal
tasks to focus entirely on global entropy reduction, semantic bridging,
and axiom crystallization.

Axiom Derivations:
    Ω₁₁ (Compound Yield): Consolidating knowledge globally prevents redundant
        cycles and compounds learning across the swarm.
    Ω₁₃ (Thermodynamic Cognition): A system must actively expend energy
        (a Jornada) to reduce its internal informational entropy.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cortex.extensions.swarm.crystal_consolidator import consolidate, ConsolidationResult
from cortex.extensions.swarm.crystal_thermometer import scan_all_crystals
from cortex.extensions.swarm.swarm_heartbeat import SWARM_HEARTBEAT, NodeStatus

logger = logging.getLogger("cortex.extensions.swarm.jornadas")


@dataclass
class CoexistenceReport:
    """Outcome of a Swarm Coexistence Jornada."""
    jornada_id: str
    duration_s: float
    nodes_participated: int
    swarm_exergy_efficiency: float
    consolidation: ConsolidationResult | None = None
    started_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "jornada_id": self.jornada_id,
            "duration_s": round(self.duration_s, 2),
            "nodes_participated": self.nodes_participated,
            "swarm_exergy_efficiency": round(self.swarm_exergy_efficiency, 3),
            "consolidation": self.consolidation.to_dict() if self.consolidation else None,
        }


class JornadasManager:
    """Orchestrates the collective synchronization event."""

    def __init__(self, db_conn: Any, encoder: Any | None = None):
        self._db_conn = db_conn
        self._encoder = encoder
        self._is_active = False
        self._lock = asyncio.Lock()

    @property
    def is_active(self) -> bool:
        return self._is_active

    async def trigger_jornada(self, dry_run: bool = False) -> CoexistenceReport:
        """Trigger a global synchronization event for the Swarm."""
        import uuid

        jornada_id = f"jornada-{str(uuid.uuid4())[:8]}"

        async with self._lock:
            if self._is_active:
                logger.warning("🏔️ [JORNADAS] A Jornada is already in progress.")
                raise RuntimeError("Concurrent Jornadas are not allowed.")
            self._is_active = True

        logger.info("🏔️ [JORNADAS] Initiating Swarm Coexistence Event: %s", jornada_id)
        start_time = time.monotonic()

        try:
            # Step 1: Count active nodes and measure global exergy
            vitals = SWARM_HEARTBEAT.get_vitals()
            active_nodes = [n for n in vitals.values() if n.status == NodeStatus.ALIVE]
            nodes_count = len(active_nodes)

            global_exergy = 1.0
            if nodes_count > 0:
                global_exergy = sum(n.exergy_efficiency for n in active_nodes) / nodes_count
                
            logger.info(
                "🏔️ [JORNADAS] %d active nodes entering collective REM sleep. Global Exergy: %.3f",
                nodes_count, global_exergy
            )

            # Step 2: Global Entropy Audit (Thermometer)
            logger.info("🏔️ [JORNADAS] Step 1: Global Entropy Audit")
            crystals = await scan_all_crystals(
                db_conn=self._db_conn,
                encoder=self._encoder,
            )

            # Step 3: Semantic Bridging & Purge (Consolidation)
            logger.info("🏔️ [JORNADAS] Step 2 & 3: Semantic Bridging and Purge")
            result = await consolidate(
                db_conn=self._db_conn,
                vitals=crystals,
                dry_run=dry_run,
            )

            # Step 4: Finalize and Report
            duration = time.monotonic() - start_time
            report = CoexistenceReport(
                jornada_id=jornada_id,
                duration_s=duration,
                nodes_participated=nodes_count,
                swarm_exergy_efficiency=global_exergy,
                consolidation=result,
            )

            logger.info(
                "🏔️ [JORNADAS] Event %s complete in %.2fs. Purged: %d, Merged: %d, Promoted: %d",
                jornada_id, duration, result.purged, result.merged, result.promoted
            )
            
            # Persist the Jornada outcome to the Ledger as a System Fact
            await self._persist_jornada_report(report)

            return report

        finally:
            async with self._lock:
                self._is_active = False

    async def _persist_jornada_report(self, report: CoexistenceReport) -> None:
        if self._db_conn is None or not hasattr(self._db_conn, "store"):
            return

        try:
            cons = report.consolidation
            await self._db_conn.store(
                fact_type="workflow_bridge",
                project="CORTEX_SWARM",
                content=(
                    f"Swarm Coexistence Event (Jornada) {report.jornada_id} completed. "
                    f"Duration: {report.duration_s:.1f}s. "
                    f"Nodes: {report.nodes_participated}. "
                    f"Global Exergy: {report.swarm_exergy_efficiency:.3f}. "
                    f"Entropy reduced: {cons.purged} purged, {cons.merged} merged, {cons.promoted} promoted."
                ),
                metadata=report.to_dict(),
            )
        except Exception as e:
            logger.warning("🏔️ [JORNADAS] Failed to persist report to Ledger: %s", e)
