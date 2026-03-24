import logging
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from cortex.ledger import SovereignLedger

logger = logging.getLogger("cortex.swarm.guards.convergence")

class ConvergenceGuards:
    """
    State Drift Detection & Convergence (Ω-Sync).
    Ensures that parallel agents in the swarm maintain a unified truth.
    """

    def __init__(self, ledger: SovereignLedger, drift_threshold: float = 0.3):
        self.ledger = ledger
        self.drift_threshold = drift_threshold
        self._global_state_hash: str | None = None
        self._last_sync = datetime.now(timezone.utc)

    def validate_state(self, agent_id: str, local_state_hash: str) -> bool:
        """
        Check if an agent's local state has drifted from the global consensus.
        """
        if not self._global_state_hash:
            self._global_state_hash = local_state_hash
            return True

        if local_state_hash != self._global_state_hash:
            logger.warning(
                "ConvergenceGuards: Drift detected in agent '%s' (Ω-Drift)", agent_id
            )
            # Record drift event in ledger
            self.ledger.record_transaction(
                project="swarm",
                action="drift_detected",
                detail={
                    "agent_id": agent_id,
                    "global_hash": self._global_state_hash,
                    "local_hash": local_state_hash
                }
            )
            return False
        
        return True

    def synchronize(self, consensus_hash: str):
        """Force a global synchronization point."""
        logger.info("ConvergenceGuards: Synchronizing global state to %s", consensus_hash)
        self._global_state_hash = consensus_hash
        self._last_sync = datetime.now(timezone.utc)
        
        self.ledger.record_transaction(
            project="swarm",
            action="global_convergence",
            detail={"consensus_hash": consensus_hash}
        )
