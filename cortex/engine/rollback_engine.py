"""Causal Rollback Engine (MVP).

Motor de control de daño perfecto. Corta ramas de ejecución enteras y 
sus dependencias causales, extirpando "dolor futuro" en el DAG.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiosqlite

from cortex.ledger.causal_graph import CausalGraph

if TYPE_CHECKING:
    from cortex.ledger.cost_field import CostField
    from cortex.ledger.execution_trace import ExecutionTraceLedger

logger = logging.getLogger("cortex.engine.rollback_engine")


class CausalRollbackEngine:
    """Implementa Selective Rewind sobre el CausalGraph."""

    def __init__(self, db_path: str, ledger: ExecutionTraceLedger, cost_field: CostField):
        self.db_path = db_path
        self.ledger = ledger
        self.cost_field = cost_field
        self.graph = CausalGraph(db_path)

    async def simulate_reversal_cost(self, event_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Calcula el costo y viabilidad de revertir el subgrafo afectado."""
        subgraph = await self.graph.compute_affected_subgraph(event_id, tenant_id)
        if not subgraph:
            return {"affected_nodes": 0, "total_reversal_cost": 0.0, "possible": False, "nodes": []}
        
        total_cost = sum(n["cost"] for n in subgraph)
        can_rollback = all(bool(n["rollback_possible"]) for n in subgraph)
        
        return {
            "affected_nodes": len(subgraph),
            "total_reversal_cost": total_cost,
            "possible": can_rollback,
            "nodes": [n["id"] for n in subgraph]
        }

    async def apply_rollback(self, event_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Aplica el rollback físico marcando el DAG como revertido."""
        sim = await self.simulate_reversal_cost(event_id, tenant_id)
        
        if not sim["possible"]:
            logger.warning(f"[Causal Rollback] FAILED para {event_id}. Subgrafo contiene nodos irreversibles.")
            return {"status": "failed", "reason": "irreversible_nodes", "details": sim}
            
        nodes = sim["nodes"]
        if not nodes:
            return {"status": "failed", "reason": "not_found", "details": sim}
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Mark all affected nodes as rolled_back
            placeholders = ",".join("?" * len(nodes))
            query = f"UPDATE execution_trace_ledger SET outcome = 'rolled_back' WHERE tenant_id = ? AND id IN ({placeholders})"
            await conn.execute(query, [tenant_id] + nodes)
            await conn.commit()
            
        logger.info(
            f"[Causal Rollback] EXITO para {event_id}. "
            f"Extirpados {len(nodes)} nodos (freed_energy={sim['total_reversal_cost']:.2f})."
        )
        return {
            "status": "success", 
            "extirpated_nodes": len(nodes), 
            "freed_energy": sim['total_reversal_cost']
        }
