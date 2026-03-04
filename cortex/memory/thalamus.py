import logging
from typing import Any

from cortex.memory.memory_retrieval import _fetch_dense_results

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

        # 2. Semantic Redundancy Check via standalone retrieval function
        try:
            # The _fetch_dense_results function is already imported at the module level.
            # No need to re-import it here.
            results = await _fetch_dense_results(
                manager=self.manager,
                tenant_id=tenant_id,
                project_id=project_id,
                query=content,
                max_episodes=5,
            )

            for fact in results or []:
                # If this is a 'knowledge' fact and we already have a 'decision'
                # on the same topic, we prioritize the decision.
                if fact_type == "knowledge" and getattr(fact, "fact_type", None) == "decision":
                    logger.info("Thalamus: Discarding knowledge redundant with decision.")
                    return False, "discard:decision_override", {"merged_with": fact.id}

                # Exact content match detection
                if getattr(fact, "content", "").strip().lower() == content.strip().lower():
                    logger.info("Thalamus: Discarding identical fact.")
                    return False, "discard:identical", {"duplicate_of": fact.id}

        except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
            # Thalamus is a pre-filter — it MUST NOT block store on any failure.
            logger.warning("Thalamus: Pre-filter scan failed (degrading gracefully): %s", e)

        return True, "encode:new", None
