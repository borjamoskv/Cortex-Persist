"""
CORTEX — Ouroboros-Ω Gate.
The thermodynamic enforcer for architectural scaling.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any, Optional

logger = logging.getLogger("cortex.extensions.gate.ouroboros")


class OuroborosGate:
    """
    Enforces the 3 Laws of Ouroboros-Ω:
    1. Landauer's Razor (Pruning the least dense module)
    2. Latency Conservation (ΔL ≤ 0)
    3. Terminal Recursion (Prompt/Logic auto-condensation)
    """

    def __init__(self, engine_conn: Any):
        self.engine = engine_conn if hasattr(engine_conn, "store") else None
        self.conn = engine_conn._get_sync_conn() if self.engine is not None else engine_conn
        self.metrics_key = "ouroboros:entropy_metrics"

    def measure_entropy(self) -> dict[str, Any]:
        """Calculates complexity metrics and signal-to-noise ratio."""
        # Simple heuristic: fact density per project
        total_facts = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        total_bridges = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'bridge'"
        ).fetchone()[0]
        total_decisions = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision'"
        ).fetchone()[0]

        # Signal density
        projects_count = self.conn.execute("SELECT COUNT(DISTINCT project) FROM facts").fetchone()[
            0
        ]

        # SNR calculation
        signal = total_decisions + total_bridges
        # We define noise as the complement of useful facts
        noise = max(1, total_facts - signal)
        snr = signal / noise

        # Absolute Entropy Index: (1/SNR) * (size/1000)
        entropy_idx = (1.0 / (snr + 0.01)) * (total_facts / 1000.0)

        return {
            "n_projects": projects_count,
            "total_facts": total_facts,
            "total_bridges": total_bridges,
            "signal_to_noise": round(snr, 3),
            "entropy_index": round(entropy_idx, 4),
            "timestamp": datetime.fromtimestamp(time.time(), tz=UTC).isoformat(),
        }

    def identify_dead_weight(self) -> Optional[str]:
        """Identifies the project or module with the lowest importance/density ratio."""
        # Analysis of projects with highest error/bridge ratio
        stats = self.conn.execute("""
            SELECT project,
                   COUNT(*) as total,
                   SUM(CASE WHEN fact_type='error' THEN 1 ELSE 0 END) as errors,
                   SUM(CASE WHEN fact_type='bridge' THEN 1 ELSE 0 END) as bridges
            FROM facts
            GROUP BY project
        """).fetchall()

        if not stats:
            return None

        # Candidates for pruning: many errors, zero bridges
        candidates = []
        for p, total, _, bridges in stats:
            if bridges == 0 and total > 5:
                candidates.append((p, total))

        if candidates:
            # Sort by total facts (higher weight in pruning)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def trigger_pruning(self, target_project: str) -> int:
        """Invalidate a specific project scope through the guarded write path."""
        logger.warning("🌀 Ouroboros-Ω: Pruning dead weight project [%s]", target_project)
        # 350/100: Sensory Feedback
        import asyncio

        try:
            from cortex.routes.notch_ws import notify_notch_pruning

            asyncio.get_running_loop().create_task(notify_notch_pruning())
        except (ImportError, RuntimeError) as e:
            logger.debug("Ouroboros pruning notification skipped: %s", e)

        if self.engine is None:
            logger.warning("Ouroboros pruning skipped: guarded engine required")
            return 0

        columns = {str(row[1]) for row in self.conn.execute("PRAGMA table_info(facts)")}
        tenant_select = "tenant_id" if "tenant_id" in columns else "'default' AS tenant_id"
        query = f"SELECT id, {tenant_select} FROM facts WHERE project = ?"
        if "is_tombstoned" in columns:
            query += " AND is_tombstoned = 0"

        fact_refs = [
            (int(row[0]), str(row[1] or "default"))
            for row in self.conn.execute(query, (target_project,)).fetchall()
        ]
        if not fact_refs:
            return 0

        from cortex.events.loop import sovereign_run

        async def _invalidate_project() -> int:
            invalidated = 0
            for fact_id, tenant_id in fact_refs:
                did_invalidate = await self.engine.invalidate(
                    fact_id,
                    reason=f"ouroboros_pruned_project:{target_project}",
                    tenant_id=tenant_id,
                )
                invalidated += int(bool(did_invalidate))
            return invalidated

        pruned_count = int(sovereign_run(_invalidate_project()))

        # Log scaling decision
        self._log_scaling_event(
            f"Tombstoned {pruned_count} facts in project {target_project} "
            "due to zero bridge density."
        )
        return pruned_count

    def _log_scaling_event(self, content: str):
        """Persists architectural scaling decisions."""
        if self.engine is None:
            logger.warning("Ouroboros scaling event not persisted: guarded engine required")
            return

        from cortex.events.loop import sovereign_run

        async def _store_event() -> int:
            return await self.engine.store(
                project="cortex",
                content=content,
                tenant_id="system",
                fact_type="decision",
                tags=["ouroboros", "scaling"],
                confidence="C5",
                source="ag:ouroboros",
                meta={"timestamp": datetime.fromtimestamp(time.time(), tz=UTC).isoformat()},
            )

        sovereign_run(_store_event())


def get_ouroboros_gate(engine: Any) -> OuroborosGate:
    """Helper to initialize the gate with an engine connection."""
    return OuroborosGate(engine)
