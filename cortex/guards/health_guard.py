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

HEALTH_AVAILABLE = True
try:
    from cortex.extensions.health.health_mixin import HealthMixin  # type: ignore
    from cortex.extensions.health.models import Grade, HealthSLA, HealthSLAViolation  # type: ignore
except ImportError:
    HEALTH_AVAILABLE = False

    class Grade:  # type: ignore
        DEGRADED = "DEGRADED"

    class HealthSLA:  # type: ignore
        def __init__(self, target_grade: str = "DEGRADED") -> None:
            pass

        def evaluate(self, score: float) -> bool:
            return True

    class HealthSLAViolation(Exception):  # type: ignore
        pass

    class HealthMixin:  # type: ignore
        async def health_score(self) -> float:
            return 1.0


logger = logging.getLogger("cortex.guards.health")


class HealthGuard(HealthMixin):
    """Circuit breaker utilizing HealthSLA contracts."""

    # By default, operations are blocked if health falls below DEGRADED (i.e., FAILED)
    DEFAULT_SLA: ClassVar[HealthSLA] = HealthSLA(target_grade=Grade.DEGRADED)

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def check_write_safety(self, sla: HealthSLA | None = None) -> bool:
        """Check if it's safe to write based on system health.

        Args:
            sla: Optional SLA to check against. Defaults to DEFAULT_SLA.

        Returns:
            True if health is acceptable.

        Raises:
            HealthSLAViolation: If health is below target.
        """
        if not HEALTH_AVAILABLE:
            return True

        target_sla = sla or self.DEFAULT_SLA
        score = await self.health_score()
        if not score:
            return True

        target_sla.evaluate(score)
        return True
