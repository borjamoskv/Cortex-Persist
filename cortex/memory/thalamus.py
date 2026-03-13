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

    def __init__(
        self,
        manager: Any,
        similarity_threshold: float = 0.92,
        min_density: int = 10,
        max_causal_children: int = 10,
    ):
        self.manager = manager
        self.similarity_threshold = similarity_threshold
        self.min_density = min_density
        self.max_causal_children = max_causal_children

    async def filter(
        self,
        content: str,
        project_id: str,
        tenant_id: str,
        fact_type: str = "general",
        parent_decision_id: int | None = None,
        conn: Any = None,
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
            results = await _fetch_dense_results(
                manager=self.manager,
                tenant_id=tenant_id,
                project_id=project_id,
                query=content,
                max_episodes=5,
            )

            for fact in results or []:
                if fact_type == "knowledge" and getattr(fact, "fact_type", None) == "decision":
                    logger.info("Thalamus: Discarding knowledge redundant with decision.")
                    return False, "discard:decision_override", {"merged_with": fact.id}

                if getattr(fact, "content", "").strip().lower() == content.strip().lower():
                    logger.info("Thalamus: Discarding identical fact.")
                    return False, "discard:identical", {"duplicate_of": fact.id}

        except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
            logger.warning("Thalamus: Pre-filter scan failed (degrading gracefully): %s", e)

        # 3. Causal Saturation Check (Entropy Containment)
        if parent_decision_id and conn:
            try:
                child_count = await self._count_children(conn, parent_decision_id, fact_type)
                if child_count >= self.max_causal_children:
                    logger.info(
                        "Thalamus: Discarding fact — causal saturation "
                        "(parent=%s, children=%d, type=%s)",
                        parent_decision_id,
                        child_count,
                        fact_type,
                    )
                    return (
                        False,
                        "discard:causal_saturation",
                        {
                            "parent_id": parent_decision_id,
                            "children": child_count,
                        },
                    )
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning(
                    "Thalamus: Causal saturation check failed (degrading gracefully): %s", e
                )

        return True, "encode:new", None

    @staticmethod
    async def _count_children(
        conn: Any,
        parent_id: int,
        fact_type: str,
    ) -> int:
        """Count how many children of a given type a parent decision has."""
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM facts WHERE parent_decision_id = ? AND fact_type = ?",
            (parent_id, fact_type),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
