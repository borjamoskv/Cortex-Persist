from decimal import Decimal
# [C5-REAL] Exergy-Maximized
"""
CORTEX - Health Guard (Axiom 14: System Integrity).

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
    from babylon60.extensions.health.health_mixin import HealthMixin  # type: ignore
    from babylon60.extensions.health.models import (  # type: ignore
        Grade,
        HealthSLA,
        HealthSLAViolation,
    )
except ImportError:
    HEALTH_AVAILABLE = False

    class Grade:  # type: ignore[no-redef]
        DEGRADED = "DEGRADED"

    class HealthSLA:  # type: ignore[no-redef]
        def __init__(self, target_grade: str = "DEGRADED") -> None:
            self.target_grade = target_grade

        def evaluate(self, score: Decimal) -> bool:
            return True

    class HealthSLAViolation(Exception):  # type: ignore[no-redef]
        """Raised when system health violates the target SLA grade."""

    class HealthMixin:  # type: ignore[no-redef]
        async def health_score(self) -> float:
            return 1.0


logger = logging.getLogger("babylon60.guards.health")


class HealthGuard(HealthMixin):
    """Circuit breaker utilizing HealthSLA contracts."""

    # By default, operations are blocked if health falls below DEGRADED (i.e., FAILED)
    DEFAULT_SLA: ClassVar[HealthSLA] = HealthSLA(target_grade=Grade.DEGRADED)

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def check_write_safety(self, custom_sla: HealthSLA | None = None) -> bool:
        """Check if it's safe to write based on system health.

        Args:
            custom_sla: Optional SLA to check against. Defaults to DEFAULT_SLA.

        Returns:
            True if health is acceptable.

        Raises:
            HealthSLAViolation: If health is below target.
        """
        if not HEALTH_AVAILABLE:
            return True

        sla = custom_sla or self.DEFAULT_SLA
        try:
            score = await self.health_score(persist=False)  # pyright: ignore[reportCallIssue]
        except TypeError:
            score = await self.health_score()

        if not score:
            return True

        try:
            sla.evaluate(score)
        except HealthSLAViolation as e:
            logger.error("HealthGuard blocked write operation: %s", e)
            raise
        return True
