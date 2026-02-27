import logging
from typing import Any

logger = logging.getLogger("cortex.memory.thalamus")


class ThalamusGate:
    """
    Sovereign pre-filtering gate for CORTEX.
    Implements active forgetting (selective encoding) BEFORE persistence.

    Philosophy: Noise is the enemy of intelligence.
    """

    def __init__(self, manager: Any, similarity_threshold: float = 0.92, min_density: int = 10):
        self.manager = manager
        self.similarity_threshold = similarity_threshold
        self.min_density = min_density

    async def filter(
        self,
        content: str,
        project_id: str,
        tenant_id: str,
        fact_type: str = "general",
    ) -> tuple[bool, str, Any | None]:
        """
        Determines if a fact should be encoded, merged, or discarded.

        Returns:
            (should_process, action_taken, metadata_patch)
        """

        # 1. Density Check (Information Theory)
        if len(content.strip()) < self.min_density:
            logger.info("Thalamus: Discarding low-density fact ('%s...')", content[:20])
            return False, "discard:low_density", None

        # 2. Semantic Redundancy Check
        # We check against the L2 vector store for recent/similar facts
        try:
            results = await self.manager._fetch_dense_results(
                tenant_id=tenant_id, project_id=project_id, query=content, max_episodes=5
            )

            for fact in results or []:
                # Logic: If high similarity, we might want to merge or discard.
                # If this is a 'knowledge' fact and we already have a 'decision'
                # on the same topic, we prioritize the decision.
                if fact_type == "knowledge" and fact.fact_type == "decision":
                    logger.info("Thalamus: Discarding knowledge redundant with decision.")
                    return False, "discard:decision_override", {"merged_with": fact.id}

                # Exact content match detection
                if fact.content.strip().lower() == content.strip().lower():
                    logger.info("Thalamus: Discarding identical fact.")
                    return False, "discard:identical", {"duplicate_of": fact.id}

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Thalamus: Pre-filter scan failed: %s", e)

        return True, "encode:new", None
