"""Autonomous Market-Making Agent (Idea #9).

Full-cycle autonomous engine that detects pre-viral signals,
scores opportunities, generates MVPs, validates demand,
and scales or kills experiments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions._quarantine.market_maker.detector import TrendDetector
    from cortex.extensions._quarantine.market_maker.models import (
        Experiment,
        ExperimentStatus,
        MVPArtifact,
        Opportunity,
        TrendSignal,
        Verdict,
    )
    from cortex.extensions._quarantine.market_maker.mvp_generator import MVPGenerator
    from cortex.extensions._quarantine.market_maker.orchestrator import MarketMakerOrchestrator
    from cortex.extensions._quarantine.market_maker.scorer import OpportunityScorer
    from cortex.extensions._quarantine.market_maker.validator import DemandValidator

__all__ = [
    "DemandValidator",
    "Experiment",
    "ExperimentStatus",
    "MVPArtifact",
    "MVPGenerator",
    "MarketMakerOrchestrator",
    "Opportunity",
    "OpportunityScorer",
    "TrendDetector",
    "TrendSignal",
    "Verdict",
]


def __getattr__(name: str) -> object:
    """Lazy imports for all public symbols."""
    # Models
    if name in (
        "Experiment",
        "ExperimentStatus",
        "MVPArtifact",
        "Opportunity",
        "TrendSignal",
        "Verdict",
    ):
        from cortex.extensions._quarantine.market_maker.models import (
            Experiment,
            ExperimentStatus,
            MVPArtifact,
            Opportunity,
            TrendSignal,
            Verdict,
        )

        _map = {
            "Experiment": Experiment,
            "ExperimentStatus": ExperimentStatus,
            "MVPArtifact": MVPArtifact,
            "Opportunity": Opportunity,
            "TrendSignal": TrendSignal,
            "Verdict": Verdict,
        }
        return _map[name]

    # Components
    if name == "TrendDetector":
        from cortex.extensions._quarantine.market_maker.detector import TrendDetector

        return TrendDetector

    if name == "OpportunityScorer":
        from cortex.extensions._quarantine.market_maker.scorer import OpportunityScorer

        return OpportunityScorer

    if name == "MVPGenerator":
        from cortex.extensions._quarantine.market_maker.mvp_generator import MVPGenerator

        return MVPGenerator

    if name == "DemandValidator":
        from cortex.extensions._quarantine.market_maker.validator import DemandValidator

        return DemandValidator

    if name == "MarketMakerOrchestrator":
        from cortex.extensions._quarantine.market_maker.orchestrator import MarketMakerOrchestrator

        return MarketMakerOrchestrator

    msg = f"module 'cortex.extensions._quarantine.market_maker' has no attribute {name!r}"
    raise AttributeError(msg)
