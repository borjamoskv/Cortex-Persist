"""
CORTEX v7 — Thalamus Gate (Pre-Persistence Admission Filter).

Implements Active Forgetting (selective encoding) BEFORE persistence.
Three deterministic filters run in sequence:

  1. Density Check   — discard facts below minimum character threshold.
  2. Redundancy Check — semantic dedup against existing L2 facts.
  3. Causal Saturation — cap children per parent decision to contain entropy.

Biological analogue: the thalamic relay nuclei gate sensory input,
preventing cortical overload by filtering noise before it reaches
the hippocampus (L2 vector store).

Derivation: Ω₂ (Entropic Asymmetry) + Ω₃ (Byzantine Default)
"""

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

        def execute_query():
            cursor = conn.execute(
                "SELECT COUNT(*) FROM facts_meta WHERE parent_decision_id = ? AND fact_type = ?",
                (str(parent_id), fact_type),
            )
            return cursor.fetchone()

        import asyncio

        row = await asyncio.to_thread(execute_query)
        return row[0] if row else 0

    async def arbitrate(
        self,
        proposals: list[dict],
        verifier: Any,
    ) -> dict | None:
        """
        Arbitrate conflicting proposals dynamically based on Bayesian Trust.
        Groups by content, sums trust scores for each content group,
        and picks the highest sum. Minority of highly trusted agents can
        outvote a majority of tainted agents.

        Args:
            proposals: List of dicts with keys ['actor_id', 'content', 'confidence_marker']
            verifier: Instance of TrustVerifier.

        Returns:
            Dictionary representing a deterministic and auditable "Decision receipt".
        """
        if not proposals:
            return None

        scores = {}
        content_scores = {}
        content_to_actors = {}

        for p in proposals:
            actor_id = p["actor_id"]
            content = p["content"]
            marker = p.get("confidence_marker")

            # 1. Fetch historical trust score for this agent
            score = await verifier.calculate_trust_score(actor_id, marker)
            scores[actor_id] = score

            if content not in content_scores:
                content_scores[content] = 0.0
                content_to_actors[content] = []

            # 2. Sum scores across agents proposing the same exact content
            content_scores[content] += score
            content_to_actors[content].append(actor_id)

        # 3. Sort descending by sum of scores, deterministic tie-break by content string
        sorted_contents = sorted(content_scores.items(), key=lambda x: (x[1], x[0]), reverse=True)

        winning_content, winning_score = sorted_contents[0]
        winning_actors = content_to_actors[winning_content]

        # 4. Tie-break winning actor (credit the most trusted one)
        winning_actors_sorted = sorted(winning_actors, key=lambda a: (scores[a], a), reverse=True)
        primary_winner = winning_actors_sorted[0]

        rejected = [p["actor_id"] for p in proposals if p["content"] != winning_content]

        reason = (
            f"Bayesian arbitration selected content with score sum {winning_score:.3f} "
            f"agreed by {len(winning_actors)} agent(s)."
        )

        # 5. Emit complete Decision Receipt
        receipt = {
            "winning_actor": primary_winner,
            "winning_content": winning_content,
            "agreed_actors": winning_actors,
            "rejected_actors": rejected,
            "weights_applied": scores,
            "content_scores": content_scores,
            "reason": reason,
        }

        logger.info(
            "Thalamus Arbitration: %s -> primary_winner=%s (Rejected: %s)",
            reason,
            primary_winner,
            len(rejected),
        )
        return receipt
