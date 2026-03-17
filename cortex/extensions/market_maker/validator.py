"""Phase 4: Demand Validation.

Simulates demand validation via micro-budget ad spend.
"""

from __future__ import annotations
from typing import Optional

import logging
import random
from decimal import Decimal

from cortex.extensions.market_maker.models import Experiment, ValidationResult

log = logging.getLogger(__name__)


class DemandValidator:
    """Simulates ad spend and tracking signups."""

    MIN_CONVERSION_RATE = Decimal("0.02")  # 2% conversion point to scale
    MAX_SPEND = Decimal("20.00")  # $20 budget per test

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self._rng = random.Random(random_seed)

    async def validate(self, experiment: Experiment) -> ValidationResult:
        """Simulates driving traffic to the MVP."""
        if experiment.mvp is None:
            raise ValueError("MVP required for validation.")

        # Simulate traffic: $20 spend at ~$0.5 CPC = ~40 visitors
        # Conversion rate random between 0.005 and 0.05
        conversion_rate = Decimal(str(round(self._rng.uniform(0.005, 0.05), 4)))
        visitors = int(self.MAX_SPEND / Decimal("0.50"))
        signups = int(Decimal(visitors) * conversion_rate)

        should_scale = conversion_rate >= self.MIN_CONVERSION_RATE

        res = ValidationResult(
            spend=self.MAX_SPEND,
            signups=signups,
            conversion_rate=conversion_rate,
            should_scale=should_scale,
        )

        log.info(
            "Validation [%s]: Spend=$%s, Signups=%d, CVR=%.2f%% -> Scale? %s",
            experiment.topic,
            res.spend,
            res.signups,
            float(res.conversion_rate * 100),
            res.should_scale,
        )

        return res
