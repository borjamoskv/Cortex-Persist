# [C5-REAL] Exergy-Maximized
import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class ExergyBifurcationEngine:
    """
    Exergy-Time Bifurcation Engine.
    Allows branching the system's reality (DAG) into multiple isolated timelines.
    Evaluates the multiverse by applying collapse through thermodynamic fitness (Exergy).
    """

    def __init__(self, ledger, scheduler):
        self.ledger = ledger
        self.scheduler = scheduler
        self.db_path = ledger.db_path

    async def spawn_timeline(self, base_tenant: str = "default") -> str:
        """Branches the current reality (base_tenant) into a new isolated timeline."""
        new_tenant = f"tl_{uuid.uuid4().hex[:6]}"

        from babylon60.database.core import connect_async

        async with await connect_async(self.db_path, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT id, origin, cost, lineage, outcome, rollback_possible, created_at FROM execution_trace_ledger WHERE tenant_id = ?",
                (base_tenant,),
            )
            rows = await cursor.fetchall()

            # Map of IDs to rewrite the lineage toward the new universe
            id_map = {row[0]: f"{row[0]}_{new_tenant}" for row in rows}

            insert_data = []
            for r in rows:
                old_id = r[0]
                new_id = id_map[old_id]
                old_lineage = json.loads(r[3])
                # Map only the ancestors that exist in this tenant
                new_lineage = json.dumps([id_map[p] for p in old_lineage if p in id_map])

                insert_data.append((new_id, new_tenant, r[1], r[2], new_lineage, r[4], r[5], r[6]))

            await conn.executemany(
                """
                INSERT INTO execution_trace_ledger 
                (id, tenant_id, origin, cost, lineage, outcome, rollback_possible, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                insert_data,
            )

            # Clone thermodynamic state (Entropy Budget)
            eb_query = "SELECT entropy_budget FROM thermodynamics_state WHERE tenant_id = ?"
            cursor = await conn.execute(eb_query, (base_tenant,))
            row = await cursor.fetchone()
            base_eb = float(row[0]) if row else 1000.0

            await conn.execute(
                "INSERT INTO thermodynamics_state (tenant_id, entropy_budget) VALUES (?, ?)",
                (new_tenant, base_eb),
            )
            await conn.commit()

        logger.info(
            f"[Bifurcation] New timeline '{new_tenant}' forged from '{base_tenant}'."
        )
        return new_tenant

    async def evaluate_multiverse(self, window_seconds: int = 3600) -> list[dict[str, Any]]:
        """
        Observes the causal multiverse.
        Calculates the global Exergy of each timeline (Fitness = Coherence * Entropy Budget).
        Allows making decisions on which realities should collapse and which prevail.
        """
        from babylon60.database.core import connect_async

        async with await connect_async(self.db_path, timeout=10) as conn:
            cursor = await conn.execute("SELECT DISTINCT tenant_id FROM thermodynamics_state")
            tenants = [row[0] for row in await cursor.fetchall()]

        multiverse_state = []
        for tenant in tenants:
            # Request the scheduler to evaluate (without acting) the global state of this universe
            tick = await self.scheduler.evaluate_tick(window_seconds, tenant)
            cf = tick["cf"]
            eb = tick["eb"]

            # Exergy Formula: Useful energy multiplied by the fraction of valid reality.
            # Schizophrenic timelines (low CF) see their energy massively depreciated.
            exergy = max(0.0, cf) * eb if eb > 0 else 0.0

            multiverse_state.append(
                {
                    "tenant_id": tenant,
                    "mode": tick["execution_mode"],
                    "cf": cf,
                    "eb": eb,
                    "exergy": exergy,
                    "drift": tick["drift"],
                }
            )

        # Sort multiverse from highest to lowest exergy fitness
        multiverse_state.sort(key=lambda x: x["exergy"], reverse=True)

        for state in multiverse_state:
            t_id = state["tenant_id"]
            if state["mode"] == "chaotic_irreversible" or state["eb"] <= 0:
                logger.critical(
                    f"[Bifurcation] Timeline '{t_id}' collapsed (Thermal Death). Exergy: 0.0"
                )
            elif state["mode"] == "coherence_lock":
                logger.warning(
                    f"[Bifurcation] Timeline '{t_id}' in Causal Quarantine (CF: {state['cf']:.2f})."
                )
            else:
                logger.info(
                    f"[Bifurcation] Timeline '{t_id}' stable. Exergy: {state['exergy']:.2f}"
                )

        return multiverse_state

    async def prune_dead_branches(self, multiverse_state: list[dict[str, Any]]) -> None:
        """Prunes from the system the timelines that have entered thermal death."""
        dead_tenants = [s["tenant_id"] for s in multiverse_state if s["exergy"] <= 0.0]
        if not dead_tenants:
            return

        from babylon60.database.core import connect_async

        async with await connect_async(self.db_path, timeout=10) as conn:
            for t in dead_tenants:
                await conn.execute("DELETE FROM execution_trace_ledger WHERE tenant_id = ?", (t,))
                await conn.execute("DELETE FROM thermodynamics_state WHERE tenant_id = ?", (t,))
                logger.warning(f"[Bifurcation] Pruned timeline '{t}' permanently from the engine.")
            await conn.commit()
