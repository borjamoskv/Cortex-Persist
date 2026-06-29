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

logger = logging.getLogger("cortex.engine.feedback.ley2_loop")


class DummyScheduler:
    """Mock scheduler to crystallize the hook while connecting to the real scheduler."""

    def adjust_weight(self, lineage: str, delta: float) -> None:
        logger.debug(f"[Ley 2 Loop] Scheduler weight adjusted for {lineage}: delta={delta:.4f}")


class Ley2Loop:
    """Closes the thermodynamic loop by injecting negative pressure into expensive paths."""

    def __init__(self, ledger: ExecutionTraceLedger, scheduler: Any = None):
        self.ledger = ledger
        self.scheduler = scheduler or DummyScheduler()

    async def apply_feedback(self, tenant_id: str = "default") -> None:
        """Extracts the thermodynamic gradient and re-injects the bias."""
        # 1. Get recent traces (limit = 500)
        traces = await self.ledger.get_recent(limit=500, tenant_id=tenant_id)
        if not traces:
            return

        pressure_map = {}

        # 2. Group by primary lineage
        for t in traces:
            lineages = t.get("lineage", [])
            if not lineages:
                continue

            # Use the root/last lineage of the array as key
            key = lineages[-1] if isinstance(lineages, list) else str(lineages)
            pressure_map.setdefault(key, []).append(t["cost"])

        # 3. Calculate median and apply damping for cold-start and attacks
        import statistics

        weights = {}
        for k, v in pressure_map.items():
            cost_median = statistics.median(v)
            weights[k] = cost_median

        # 4. Re-inject bias in the scheduler
        for lineage, weight in weights.items():
            # Oscillation damping (0.85)
            delta = -weight * 0.85
            self.scheduler.adjust_weight(lineage=lineage, delta=delta)
