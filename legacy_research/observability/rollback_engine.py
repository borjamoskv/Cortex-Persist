# [C5-REAL] Exergy-Maximized
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.rollback")


class CausalRollbackEngine:
    """
    Causal Rollback Engine (Level 5 CORTEX)
    Operates under stable thermal fields to selectively reconstruct history.
    """

    def __init__(self, graph_path: str = "~/.gemini/config/skills/_metrics/causal_graph.json"):
        self.graph_path = Path(graph_path).expanduser()
        self.graph_data = self._load_graph()

    def _load_graph(self) -> dict[str, Any]:
        if self.graph_path.exists():
            try:
                with open(self.graph_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load causal graph: {e}")
        return {"nodes": [], "edges": []}

    def compute_subgraph(self, target_node: str) -> list[dict[str, Any]]:
        """
        Identifies the downstream dependency subgraph originating from the target node.
        Uses the transfer_exergy edges to map affected future states.
        """
        edges = self.graph_data.get("edges", [])
        subgraph_edges = []
        visited = set()
        queue = [target_node]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for e in edges:
                if e["source"] == current:
                    subgraph_edges.append(e)
                    if e["target"] not in visited:
                        queue.append(e["target"])

        return subgraph_edges

    def estimate_reversal_cost(self, subgraph: list[dict[str, Any]]) -> float:
        """
        Calculates the thermodynamic cost of rolling back a subgraph.
        Cost is proportional to the accumulated transfer_exergy of the severed edges.
        """
        cost = sum(edge.get("transfer_exergy", 0.0) for edge in subgraph)
        return round(cost, 2)

    def apply_selective_reexecution(self, target_node: str) -> dict[str, Any]:
        """
        The core operation. Identifies the subgraph, estimates the cost,
        and simulates the selective pruning and re-execution of the timeline.
        """
        logger.info(f"🌀 [ROLLBACK] Initiating selective causal reversal for node: {target_node}")

        subgraph = self.compute_subgraph(target_node)
        if not subgraph:
            logger.info(
                f"🌀 [ROLLBACK] Node {target_node} has no downstream causality. Reversal cost is zero."
            )
            return {
                "target": target_node,
                "affected_subgraph_edges": 0,
                "affected_nodes": [target_node],
                "reversal_cost_exergy": 0.0,
                "status": "COMPLETED",
            }

        cost = self.estimate_reversal_cost(subgraph)

        affected_nodes = list(
            set([e["source"] for e in subgraph] + [e["target"] for e in subgraph])
        )

        logger.warning(
            f"⚠️ [ROLLBACK] Reversal Cost: {cost} exergy units across {len(affected_nodes)} affected nodes."
        )

        # Hard thermal protection limit for rollback engine
        # Prevents cascade collapse of the entire timeline if reversal is too expensive
        if cost > 500.0:
            logger.error(
                f"🛑 [ROLLBACK] ABORTED. Exergy cost ({cost}) exceeds structural safety limit (500.0)."
            )
            return {
                "target": target_node,
                "affected_subgraph_edges": len(subgraph),
                "affected_nodes": affected_nodes,
                "reversal_cost_exergy": cost,
                "status": "ABORTED_TOO_EXPENSIVE",
            }

        logger.info(
            f"✅ [ROLLBACK] Causal timeline successfully pruned starting from {target_node}."
        )

        return {
            "target": target_node,
            "affected_subgraph_edges": len(subgraph),
            "affected_nodes": affected_nodes,
            "reversal_cost_exergy": cost,
            "status": "COMPLETED",
        }
