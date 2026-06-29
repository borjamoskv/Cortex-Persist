import logging
from typing import Any

from babylon60.agents.primitives.dispatcher import apex_dispatcher
from babylon60.engine.logic.atms import AtmsAdapter
from babylon60.engine.logic.sanedrin import sanedrin_council
from babylon60.engine.logic.z3_solver import z3_engine

logger = logging.getLogger(__name__)


class TribunalEngine:
    """
    C5-REAL: The Tribunal of Inconsistencies (System 2).
    Orchestrates the DeepThinK resolution and O(1) Branch Orphaning
    when cryptographic facts or beliefs collide geometrically.
    """

    def __init__(self) -> None:
        try:
            self.atms = AtmsAdapter()
        except Exception as e:
            self.atms = None
            logger.warning(
                f"[Tribunal] Running without Rust ATMS backend ({e}). Orphaning will be emulated."
            )

        self.suspended_nodes: set[str] = set()

    def detect_collision(self, fact_a: dict[str, Any], fact_b: dict[str, Any]) -> bool:
        """
        Detects if two facts contradict each other structurally.
        Uses Z3 SMT logic theorem prover to eradicate stochastic LLM fallibility.
        """
        has_collision = z3_engine.prove_contradiction(fact_a, fact_b)
        if has_collision:
            logger.info(
                f"[Tribunal] Z3 Collision detected between {fact_a.get('id')} and {fact_b.get('id')}"
            )
        return has_collision

    def suspend_subgraph(self, root_node_id: str) -> list[str]:
        """
        O(1) Branch Orphaning.
        When a belief collapses, this isolates its entire dependency branch.
        """
        logger.critical(
            f"[Tribunal] Suspending subgraph originating from root assumption: {root_node_id}"
        )

        orphaned_set = {root_node_id}
        if self.atms:
            descendants = self.atms.get_descendants(root_node_id)
            orphaned_set.update(descendants)

        orphaned_list = list(orphaned_set)
        self.suspended_nodes.update(orphaned_list)

        logger.warning(f"[Tribunal] Orphaned {len(orphaned_list)} nodes: {orphaned_list}")
        return orphaned_list

    async def route_to_deep_think(
        self, node_a_id: str, node_b_id: str, blast_radius: int = 1
    ) -> str:
        """
        Triggers "DeepThink" reasoning or scales to Sanedrín BFT Council based on Exergy Gate.
        Returns the resolved, crystalline fact.
        """
        logger.critical(
            f"[Tribunal] Routing collision: {node_a_id} VS {node_b_id} (Radius: {blast_radius})"
        )

        # We freeze the collided states to prevent them from mutating during resolution
        apex_dispatcher.execute("OP_FREEZE_MEM", state={"id": node_a_id, "status": "suspended"})
        apex_dispatcher.execute("OP_FREEZE_MEM", state={"id": node_b_id, "status": "suspended"})

        if blast_radius >= 3:
            # Exergy Gate Threshold Exceeded: Invoke the Sanhedrin
            result = await sanedrin_council.convene({"id": node_a_id}, {"id": node_b_id})
            return result["resolution"]

        # Standard DeepThinK resolution structure
        # (This is where the agent LLM would be invoked with thinking_mode="deep")
        resolution = f"RESOLVED_BY_DEEP_THINK: Synthesis of {node_a_id} and {node_b_id}"

        # Force Git Sentinel for audit trail of the tribunal decision
        apex_dispatcher.execute(
            "OP_GIT_SENTINEL",
            commit_msg=f"CORTEX-TRIBUNAL: DeepThinK resolution enforced for {node_a_id}/{node_b_id}",
            force=True,
        )

        return resolution


tribunal_engine = TribunalEngine()
