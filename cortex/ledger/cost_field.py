"""Cost Field - Extractor de gradiente termodinámico.

Convierte las trazas de ejecución en campos de energía que permiten 
penalizar o favorecer rutas (lineages) futuras según su costo histórico.
"""

from __future__ import annotations

import logging
from statistics import mean, median
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.ledger.execution_trace import ExecutionTraceLedger

logger = logging.getLogger("cortex.ledger.cost_field")


class CostField:
    """Interpreta la energía de las trazas de ejecución."""

    def __init__(self, ledger: ExecutionTraceLedger):
        self.ledger = ledger

    async def compute_cost_gradient(self, lineage_hash: str, tenant_id: str = "default") -> dict[str, float]:
        """Calcula la presión y varianza de costo para un linaje."""
        traces = await self.ledger.query_by_lineage(lineage_hash, tenant_id=tenant_id)

        if not traces:
            return {
                "cost_pressure": 0.0, 
                "variance": 0.0,
                "median_pressure": 0.0
            }

        costs = [t["cost"] for t in traces]

        return {
            "cost_pressure": mean(costs),
            "variance": (max(costs) - min(costs)) if costs else 0.0,
            "median_pressure": median(costs)
        }
