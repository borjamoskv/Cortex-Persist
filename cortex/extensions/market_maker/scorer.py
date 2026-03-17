"""Phase 2: Opportunity Scorer.

Evaluates signals on 4 axes: TAM, Competition, Advantage, and Time-To-Market.
Strict scoring bounds to yield exact `Verdict` directives.
"""

from __future__ import annotations
from typing import Optional

import logging
import random
from decimal import Decimal

from cortex.extensions.market_maker.models import Opportunity, TrendSignal, Verdict

log = logging.getLogger(__name__)


class OpportunityScorer:
    """Motor de evaluación multidimensional de oportunidades."""

    EXECUTE_THRESHOLD = Decimal("70")
    MONITOR_THRESHOLD = Decimal("40")

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self._rng = random.Random(random_seed)

    async def score(self, signal: TrendSignal) -> Opportunity:
        """
        Evalúa 4 ejes hasta 25 ptos c/u: TAM, Competición, Ventaja CORTEX, y TTM.
        """
        # Simulamos la evaluación de cada eje de forma determinista para la demostración automátizada.
        tam = Decimal(str(round(self._rng.uniform(5, 25), 2)))
        comp = Decimal(str(round(self._rng.uniform(5, 25), 2)))
        adv = Decimal(str(round(self._rng.uniform(5, 25), 2)))
        ttm = Decimal(str(round(self._rng.uniform(5, 25), 2)))

        total = tam + comp + adv + ttm

        if total >= self.EXECUTE_THRESHOLD:
            verdict = Verdict.EXECUTE
        elif total >= self.MONITOR_THRESHOLD:
            verdict = Verdict.MONITOR
        else:
            verdict = Verdict.IGNORE

        log.debug(
            "Scored '%s': Total=%.2f (TAM=%.1f, CMP=%.1f, ADV=%.1f, TTM=%.1f) -> %s",
            signal.topic,
            float(total),
            float(tam),
            float(comp),
            float(adv),
            float(ttm),
            verdict.name,
        )

        return Opportunity(
            signal=signal,
            tam_score=tam,
            competition_score=comp,
            advantage_score=adv,
            ttm_score=ttm,
            total_score=total,
            verdict=verdict,
        )
