# [C5-REAL] Exergy-Maximized
import json
import logging
import uuid
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class ExergyBifurcationEngine:
    """
    Exergy-Time Bifurcation Engine.
    Permite ramificar la realidad del sistema (DAG) en múltiples timelines aisladas.
    Evalúa el multiverso aplicando colapso por fitness termodinámico (Exergy).
    """

    def __init__(self, ledger, scheduler):
        self.ledger = ledger
        self.scheduler = scheduler
        self.db_path = ledger.db_path

    async def spawn_timeline(self, base_tenant: str = "default") -> str:
        """Ramifica la realidad actual (base_tenant) en una nueva línea temporal aislada."""
        new_tenant = f"tl_{uuid.uuid4().hex[:6]}"

        from cortex.database.core import connect_async
        async with await connect_async(self.db_path, timeout=10) as conn:
            cursor = await conn.execute(
                "SELECT id, origin, cost, lineage, outcome, rollback_possible, created_at FROM execution_trace_ledger WHERE tenant_id = ?",
                (base_tenant,),
            )
            rows = await cursor.fetchall()

            # Mapa de IDs para reescribir el linaje hacia el nuevo universo
            id_map = {row[0]: f"{row[0]}_{new_tenant}" for row in rows}

            insert_data = []
            for r in rows:
                old_id = r[0]
                new_id = id_map[old_id]
                old_lineage = json.loads(r[3])
                # Mapear solo los ancestros que existen en este tenant
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

            # Clonar estado termodinámico (Entropy Budget)
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
            f"[Bifurcation] Nueva línea temporal '{new_tenant}' forjada a partir de '{base_tenant}'."
        )
        return new_tenant

    async def evaluate_multiverse(self, window_seconds: int = 3600) -> list[dict[str, Any]]:
        """
        Observa el multiverso causal.
        Calcula la Exergía global de cada timeline (Fitness = Coherencia * Presupuesto de Entropía).
        Permite tomar decisiones sobre qué realidades deben colapsar y cuáles prevalecen.
        """
        from cortex.database.core import connect_async
        async with await connect_async(self.db_path, timeout=10) as conn:
            cursor = await conn.execute("SELECT DISTINCT tenant_id FROM thermodynamics_state")
            tenants = [row[0] for row in await cursor.fetchall()]

        multiverse_state = []
        for tenant in tenants:
            # Pedimos al scheduler que evalúe (sin actuar) el estado global de este universo
            tick = await self.scheduler.evaluate_tick(window_seconds, tenant)
            cf = tick["cf"]
            eb = tick["eb"]

            # Fórmula de Exergía: Energía útil multiplicada por la fracción de realidad válida.
            # Timelines esquizofrénicas (bajo CF) ven su energía depreciada masivamente.
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

        # Ordenar multiverso de mayor a menor fitness exergético
        multiverse_state.sort(key=lambda x: x["exergy"], reverse=True)

        for state in multiverse_state:
            t_id = state["tenant_id"]
            if state["mode"] == "chaotic_irreversible" or state["eb"] <= 0:
                logger.critical(
                    f"[Bifurcation] Timeline '{t_id}' colapsada (Muerte Térmica). Exergy: 0.0"
                )
            elif state["mode"] == "coherence_lock":
                logger.warning(
                    f"[Bifurcation] Timeline '{t_id}' en Cuarentena Causal (CF: {state['cf']:.2f})."
                )
            else:
                logger.info(
                    f"[Bifurcation] Timeline '{t_id}' estable. Exergy: {state['exergy']:.2f}"
                )

        return multiverse_state

    async def prune_dead_branches(self, multiverse_state: list[dict[str, Any]]) -> None:
        """Purga del sistema las timelines que han entrado en muerte térmica."""
        dead_tenants = [s["tenant_id"] for s in multiverse_state if s["exergy"] <= 0.0]
        if not dead_tenants:
            return

        from cortex.database.core import connect_async
        async with await connect_async(self.db_path, timeout=10) as conn:
            for t in dead_tenants:
                await conn.execute("DELETE FROM execution_trace_ledger WHERE tenant_id = ?", (t,))
                await conn.execute("DELETE FROM thermodynamics_state WHERE tenant_id = ?", (t,))
                logger.warning(f"[Bifurcation] Pruned timeline '{t}' permanentemente del motor.")
            await conn.commit()
