# [C5-REAL] Exergy-Maximized
"""Causal Scheduler - Time pressure function and DAG stability.

Execution arbiter. Decides when the system evolves and when the
state freezes (via macro-rewinds or micro-repairs) based on
the 'permission_to_exist_score'.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from babylon60.database.core import connect_async_ctx

if TYPE_CHECKING:
    from babylon60.engine.core.rollback_engine import CausalRollbackEngine
    from babylon60.ledger.causal_graph import CausalGraph
    from babylon60.ledger.execution_trace import ExecutionTraceLedger

logger = logging.getLogger("cortex.engine.flow.causal_scheduler")


class CausalScheduler:
    """Living thermodynamics orchestrator. Dictates the global execution_mode."""

    def __init__(
        self,
        causal_graph: CausalGraph,
        rollback_engine: CausalRollbackEngine,
        ledger: ExecutionTraceLedger,
        rollback_threshold: float = 100.0,
        permission_kill_threshold: float = 0.05,
    ):
        self.graph = causal_graph
        self.rollback = rollback_engine
        self.ledger = ledger

        # Risk threshold (impact * propagation) > 100 defaults to trigger
        self.rollback_threshold = rollback_threshold

        # Any trace with permission_to_exist_score < 0.05 is an immediate macro-rewind candidate
        self.permission_kill_threshold = permission_kill_threshold

        # Coherence thresholds
        self.cf_threshold = 0.92
        self.base_entropy_budget = 1000.0

    async def _get_entropy_budget(self, tenant_id: str) -> float:
        """Gets historical EB. If it does not exist, initializes it."""
        # Stored in the trace db for MVP convenience
        init_query = "CREATE TABLE IF NOT EXISTS thermodynamics_state (tenant_id TEXT PRIMARY KEY, entropy_budget REAL)"
        async with connect_async_ctx(self.ledger.db_path) as conn:
            await conn.execute(init_query)
            cursor = await conn.execute(
                "SELECT entropy_budget FROM thermodynamics_state WHERE tenant_id = ?", (tenant_id,)
            )
            row = await cursor.fetchone()
            if not row:
                await conn.execute(
                    "INSERT OR IGNORE INTO thermodynamics_state (tenant_id, entropy_budget) VALUES (?, ?)",
                    (tenant_id, self.base_entropy_budget),
                )
                await conn.commit()
                return self.base_entropy_budget
            return float(row[0])

    async def _update_entropy_budget(self, tenant_id: str, new_budget: float) -> None:
        async with connect_async_ctx(self.ledger.db_path) as conn:
            await conn.execute(
                "UPDATE thermodynamics_state SET entropy_budget = ? WHERE tenant_id = ?",
                (new_budget, tenant_id),
            )
            await conn.commit()

    async def evaluate_tick(
        self, window_seconds: int = 3600, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Evaluates system state and global ontological continuity (GCC)."""
        drift = await self.graph.compute_global_drift(window_seconds, tenant_id)
        cf = await self.graph.compute_coherence_field(window_seconds, tenant_id)
        eb = await self._get_entropy_budget(tenant_id)

        risk_map = await self.graph.compute_node_risk_scores(window_seconds, tenant_id)

        candidates = [
            n
            for n in risk_map
            if n["risk_score"] > self.rollback_threshold
            or n["permission_to_exist_score"] < self.permission_kill_threshold
        ]

        # GCC Core Decision Matrix
        # 1. Entropy Exhaustion (Chaos breakdown)
        if eb < 0.0:
            mode = "chaotic_irreversible"
            candidates = []  # Defensive operations forbidden, the whole system burns
        # 2. Coherence collapse (Reality fragmentation)
        elif cf < self.cf_threshold:
            mode = "coherence_lock"
            candidates = []  # Block new rollbacks to reconcile first
        # 3. Structural runaway
        elif drift > 50.0 and len(candidates) >= 3:
            mode = "collapse_prevent"
        # 4. Drift growing
        elif drift > 20.0 or len(candidates) > 0:
            mode = "pressure"
        # 5. Stable
        else:
            mode = "stable"

        # Update EB roughly based on drift vs rollback costs (drift gain adds to budget)
        # A manageable drift adds budget, a high drift consumes entropy
        drift_gain = (20.0 - drift) * 0.1
        # EB mutation applies immediately to reflect thermodynamic time
        new_eb = eb + drift_gain
        await self._update_entropy_budget(tenant_id, new_eb)

        logger.debug(
            "[Causal Scheduler] Tick Evaluated | Mode: %s | CF: %.2f | EB: %.2f | Drift: %.2f | Candidates: %d",
            mode,
            cf,
            new_eb,
            drift,
            len(candidates),
        )

        return {
            "drift": drift,
            "cf": cf,
            "eb": new_eb,
            "rollback_candidates": candidates,
            "execution_mode": mode,
        }

    async def tick_and_act(
        self, window_seconds: int = 3600, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Evaluates the tick and executes actions if global permission exists."""
        tick_state = await self.evaluate_tick(window_seconds, tenant_id)

        mode = tick_state["execution_mode"]
        actions_taken = []

        if mode == "chaotic_irreversible":
            logger.critical(
                "[Causal Scheduler] ENTROPY BUDGET < 0. System in irreversible chaos. Rollbacks suspended."
            )

        elif mode == "coherence_lock":
            logger.warning(
                f"[Causal Scheduler] COHERENCE FIELD < {self.cf_threshold}. Blocking mutations until causal reconciliation."
            )

        elif mode == "collapse_prevent":
            # P0: Macro-rewind for all critical candidates to save the system DAG
            candidates = tick_state["rollback_candidates"]
            candidates.sort(key=lambda x: x["risk_score"], reverse=True)

            total_rollback_cost = 0.0
            for c in candidates:
                logger.warning(
                    f"[Causal Scheduler] Defensive Macro-Rewind for {c['id']} "
                    f"(permission_to_exist={c['permission_to_exist_score']:.3f})"
                )
                res = await self.rollback.apply_rollback(c["id"], tenant_id=tenant_id)
                actions_taken.append({"target": c["id"], "result": res})

                if res.get("status") == "success":
                    total_rollback_cost += res.get("freed_energy", 0.0)

            # Subtract rollback cost from Entropy Budget
            if total_rollback_cost > 0:
                eb = tick_state["eb"]
                await self._update_entropy_budget(tenant_id, eb - total_rollback_cost)

        elif mode == "pressure":
            # Micro-repair / Logging / Allow Ley2Loop to handle it via future bias
            logger.info(
                "[Causal Scheduler] Pressure state. Relying on Ley2Loop for drift shaping."
            )

        return {"tick_state": tick_state, "actions": actions_taken}
