"""CORTEX v5.0 — Consensus.

Neural Swarm Consensus and Reputation-Weighted validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cortex.consensus.manager import ConsensusManager

if TYPE_CHECKING:
    from cortex.consensus.reputation import ReputationManager
    from cortex.consensus.trust import TrustGraph
else:
    # Runtime optional loading
    ReputationManager: Any = None
    TrustGraph: Any = None
    try:
        from cortex.consensus.reputation import ReputationManager as _RM
        ReputationManager = _RM
    except ImportError:
        pass
    try:
        from cortex.consensus.trust import TrustGraph as _TG
        TrustGraph = _TG
    except ImportError:
        pass

__all__ = ["ConsensusManager", "ReputationManager", "TrustGraph"]
