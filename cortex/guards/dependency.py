# [C5-REAL] Exergy-Maximized
"""
Scaffolding AI (Andamiaje Adaptativo)

Controlled incremental exposure of EDG nodes. Decomposes complex failure matrices
into orthogonal sub-primitives, reducing cognitive load until a validated success node is reached.
"""

from typing import Any


class ScaffoldingGuard:
    def __init__(self, edg_topology: dict[str, Any]):
        self.edg = edg_topology

    def evaluate_failure(self, student_id: str, failed_node_id: str) -> list[str]:
        """
        When a complex assertion fails, decomposes the node into orthogonal sub-primitives.
        Returns a sequence of simpler nodes to rebuild the scaffolding.
        """
        node_data = self.edg.get(failed_node_id)
        if not node_data:
            return []

        # Extract dependencies (sub-primitives)
        dependencies = node_data.get("dependencies", [])

        # Sort dependencies by cyclomatic complexity to offer the easiest first
        orthogonal_path = sorted(
            dependencies, key=lambda dep_id: self.edg.get(dep_id, {}).get("complexity", 999)
        )

        return orthogonal_path

    def scaffold_next_step(self, student_id: str, current_failure_path: list[str]) -> str:
        """Returns the immediate next node to attempt in the orthogonal path."""
        if not current_failure_path:
            return None
        return current_failure_path[0]
