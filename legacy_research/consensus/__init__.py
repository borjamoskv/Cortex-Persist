# [C5-REAL] Exergy-Maximized
"""Consensus.

Neural Swarm Consensus and Reputation-Weighted validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from legacy_research.consensus.manager import ConsensusManager

if TYPE_CHECKING:
    from legacy_research.consensus.reputation import (
        ReputationManager,  # pyright: ignore[reportMissingImports]
    )
    from legacy_research.consensus.trust import TrustGraph  # pyright: ignore[reportMissingImports]
else:
    # Runtime optional loading
    ReputationManager: Any = None
    TrustGraph: Any = None
    try:
        from legacy_research.consensus.reputation import ReputationManager as _RM

        ReputationManager = _RM
    except ImportError:
        import logging

    try:
        from legacy_research.consensus.trust import TrustGraph as _TG

        TrustGraph = _TG
    except ImportError:
        import logging


__all__ = ["ConsensusManager", "ReputationManager", "TrustGraph"]
