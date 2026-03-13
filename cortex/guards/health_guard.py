"""
CORTEX — Health Guard (Axiom 14: System Integrity).

Circuit breaker that blocks writes or intense operations if the
underlying system health is degraded or failing. This prevents entropy
cascades (e.g., trying to write to a massive/corrupted DB).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from cortex.health.health_mixin import HealthMixin
from cortex.health.models import Grade, HealthSLA, HealthSLAViolation

logger = logging.getLogger("cortex.guards.health")


class HealthGuard(HealthMixin):
    """Circuit breaker utilizing HealthSLA contracts."""

    # By default, operations are blocked if health falls below DEGRADED (i.e., FAILED)
    DEFAULT_SLA: ClassVar[HealthSLA] = HealthSLA(target_grade=Grade.DEGRADED)

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def check_write_safety(self, custom_sla: HealthSLA | None = None) -> None:
        """Verify the database is healthy enough to receive writes.

        Args:
            custom_sla: Override the default SLA requirement.

        Raises:
            HealthSLAViolation: If health is too poor to proceed safely.
        """
        sla = custom_sla or self.DEFAULT_SLA

        # We only want the score, so HealthMixin.health_score() is perfect
        score = await self.health_score()

        try:
            sla.evaluate(score)
        except HealthSLAViolation as e:
            logger.error("HealthGuard blocked write operation: %s", e)
            raise
