# [C5-REAL] Exergy-Maximized
"""Ley 2 Loop: Expensive Errors First (Kernel de Re-weighting Termodinámico).

Aplica la selección evolutiva re-inyectando bias en base al costo real
de los linajes de ejecución.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon60.ledger.execution_trace import ExecutionTraceLedger

logger = logging.getLogger("babylon60.engine.feedback.ley2_loop")


class DummyScheduler:
    """Mock scheduler para cristalizar el hook mientras se conecta al scheduler real."""

    def adjust_weight(self, lineage: str, delta: float) -> None:
        logger.debug(f"[Ley 2 Loop] Scheduler weight adjusted for {lineage}: delta={delta:.4f}")


class Ley2Loop:
    """Cierra el bucle termodinámico inyectando presión negativa a caminos caros."""

    def __init__(self, ledger: ExecutionTraceLedger, scheduler: Any = None):
        self.ledger = ledger
        self.scheduler = scheduler or DummyScheduler()

    async def apply_feedback(self, tenant_id: str = "default") -> None:
        """Extrae el gradiente termodinámico y re-inyecta el bias."""
        # 1. Obtener trazas recientes (limit = 500)
        traces = await self.ledger.get_recent(limit=500, tenant_id=tenant_id)
        if not traces:
            return

        pressure_map = {}

        # 2. Agrupar por lineage primario
        for t in traces:
            lineages = t.get("lineage", [])
            if not lineages:
                continue

            # Usar el root/último lineage del array como key
            key = lineages[-1] if isinstance(lineages, list) else str(lineages)
            pressure_map.setdefault(key, []).append(t["cost"])

        # 3. Calcular mediana y aplicar damping para cold-start y ataques
        import statistics

        weights = {}
        for k, v in pressure_map.items():
            cost_median = statistics.median(v)
            weights[k] = cost_median

        # 4. Re-inyectar bias en el scheduler
        for lineage, weight in weights.items():
            # Oscillation damping (0.85)
            delta = -weight * 0.85
            self.scheduler.adjust_weight(lineage=lineage, delta=delta)
