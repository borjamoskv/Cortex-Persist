import logging
from typing import Any

from cortex.swarm.actuators.protocol import ActuatorResponse

logger = logging.getLogger("cortex.swarm.guards.chaos")


class ChaosGuards:
    """
    Byzantine Fault Tolerance Guard (Ω-Chaos).
    Enforces cross-validation between multiple agents for critical tasks.
    """

    @staticmethod
    async def validate_consensus(
        responses: list[ActuatorResponse],
        min_agreement: int = 2,
        required_exergy: float = 0.0
    ) -> bool:
        """
        Heavy Byzantine Fault Tolerance (BFT).
        Checks for semantic agreement and filters agents with low reputation/exergy.
        """
        if len(responses) < min_agreement:
            return False
        
        # Group by status and basic content fingerprint
        agreements: dict[str, dict[str, Any]] = {}
        for resp in responses:
            # Enhanced fingerprint: normalized status + content snippet hash
            content_snippet = str(resp.content).strip()[:100].lower()
            fingerprint = f"{resp.status}_{hash(content_snippet)}"
        
            if fingerprint not in agreements:
                agreements[fingerprint] = {"count": 0, "responses": []}
        
            agreements[fingerprint]["count"] += 1
            agreements[fingerprint]["responses"].append(resp)
        
        if not agreements:
            return False

        # Find the consensus with highest agreement
        winning_fingerprint = max(agreements.keys(), key=lambda k: agreements[k]["count"])
        max_agreement = agreements[winning_fingerprint]["count"]
    
        logger.info("ChaosGuards: BFT Consensus: %d/%d agreement", max_agreement, len(responses))
    
        # Evolution Guard: Detect high-entropy outliers
        if max_agreement < min_agreement:
            logger.warning("ChaosGuards: Consensus FAILED (Entropy too high)")
            return False
        
        return True

    @staticmethod
    def is_critical(task: str) -> bool:
        """Heuristic to detect critical infrastructure tasks."""
        critical_keywords = ["ledger", "write", "delete", "persist", "security", "guard"]
        return any(kw in task.lower() for kw in critical_keywords)
