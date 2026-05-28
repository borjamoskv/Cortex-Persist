"""Phase 5: Full Cycle Orchestrator.

Ties all 4 phases together: Detect -> Score -> Generate -> Validate.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from cortex.extensions.market_maker.detector import TrendDetector
from cortex.extensions.market_maker.models import (
    Experiment,
    ExperimentStatus,
    Opportunity,
    Verdict,
)
from cortex.extensions.market_maker.mvp_generator import MVPGenerator
from cortex.extensions.market_maker.scorer import OpportunityScorer
from cortex.extensions.market_maker.validator import DemandValidator

log = logging.getLogger(__name__)


class MarketMakerOrchestrator:
    """End-to-end engine for the Autonomous Market Maker."""

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self.detector = TrendDetector(random_seed=random_seed)
        self.scorer = OpportunityScorer(random_seed=random_seed)
        self.generator = MVPGenerator()
        self.validator = DemandValidator(random_seed=random_seed)
        self._experiments: dict[str, Experiment] = {}

    async def run_cycle(
        self,
        keywords: list[str],
        dry_run: bool = False,
    ) -> list[Experiment]:
        """
        Ejecuta el ciclo completo.

        1. Detect
        2. Score
        3. Generar MVP (Solo si Verdict == EXECUTE)
        4. Validar Demanda
        5. Decidir Scale / Kill
        """
        log.info("Iniciando Market Maker Cycle para %d keywords...", len(keywords))

        # Phase 1
        signals = await self.detector.scan(keywords)
        if not signals:
            log.info("Cycle completado: no se detectó convergencia.")
            return []

        # Phase 2
        opportunities: list[Opportunity] = []
        for sig in signals:
            opp = await self.scorer.score(sig)
            opportunities.append(opp)

        # Phase 3, 4, 5
        active_experiments: list[Experiment] = []
        for opp in opportunities:
            exp = Experiment(
                id=uuid.uuid4().hex[:8],
                topic=opp.signal.topic,
                status=ExperimentStatus.SCORED,
                opportunity=opp,
            )
            self._experiments[exp.id] = exp
            active_experiments.append(exp)

            if opp.verdict != Verdict.EXECUTE:
                log.debug(
                    "Oportunidad '%s' descartada (Verdict=%s).",
                    exp.topic,
                    opp.verdict.name,
                )
                exp.status = ExperimentStatus.KILLED
                continue

            # Phase 3
            mvp = await self.generator.generate(opp)
            exp.mvp = mvp
            exp.status = ExperimentStatus.MVP_GENERATED

            if not dry_run:
                # Phase 4
                exp.status = ExperimentStatus.VALIDATING
                val = await self.validator.validate(exp)
                exp.validation = val

                # Phase 5
                if val.should_scale:
                    exp.status = ExperimentStatus.SCALED
                else:
                    exp.status = ExperimentStatus.KILLED

            await self._persist_learning(exp)

        log.info(
            "Market Maker Cycle completado. %d experimentos procesados.",
            len(active_experiments),
        )
        return active_experiments

    async def _persist_learning(self, experiment: Experiment) -> None:
        """Integra con CORTEX Core Engine para persistir aprendizajes."""
        log.debug("Persistiendo fact en memory (mock) para exp %s", experiment.id)

    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        return self._experiments.get(exp_id)
