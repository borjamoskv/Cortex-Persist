# [C5-REAL] Exergy-Maximized
"""
CORTEX Persist TDA Subsystem — Hodge Memory Routing Engine.
Implements RecallVectorField and geodesic descent over the memory graph
using exergy-weighted gradients and zero-mode transport alignment.

Reality Level: C5-REAL
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Final

DB_PATH: Final[Path] = Path("/Users/borjafernandezangulo/.cortex/cortex.db")


class HodgeMemoryRouter:
    """
    Orchestrates memory graph traversal using geodesic descent on the
    RecallVectorField, bounded by exergy gradients.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def load_memory_graph(self) -> tuple[dict[int, dict[str, Any]], dict[int, list[int]]]:
        """
        Loads facts (nodes) and causal_edges (edges) from CORTEX.
        Returns:
            nodes: map from fact_id -> fact_dict
            edges: adjacency list mapping node_id -> list of child_ids
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load nodes
        cursor.execute(
            "SELECT id, project, exergy_score, content FROM facts WHERE is_tombstoned = 0"
        )
        nodes = {}
        for row in cursor.fetchall():
            fact_id, project, exergy_score, content = row
            nodes[fact_id] = {
                "id": fact_id,
                "project": project,
                "exergy_score": float(exergy_score),
                "content": content,
            }

        # Load edges
        cursor.execute("SELECT fact_id, parent_id FROM causal_edges")
        edges: dict[int, list[int]] = {n_id: [] for n_id in nodes}
        for row in cursor.fetchall():
            fact_id, parent_id = row
            if parent_id in edges and fact_id in nodes:
                edges[parent_id].append(fact_id)

        conn.close()
        return nodes, edges

    def compute_recall_potential(
        self, nodes: dict[int, dict[str, Any]], edges: dict[int, list[int]], target_ids: list[int]
    ) -> dict[int, float]:
        """
        Computes the potential field V(x) for each node based on the targets.
        V(x) = sum_{y in targets} (exergy(y) / (shortest_path_distance(x, y) + 1.0))
        """
        potential = dict.fromkeys(nodes, 0.0)

        # Simple BFS-based shortest path distance computation
        for target in target_ids:
            if target not in nodes:
                continue

            # BFS to find distances
            distances = {target: 0}
            queue = [target]
            while queue:
                current = queue.pop(0)
                curr_dist = distances[current]

                # We traverse backward (children to parents) to pull potential
                # Find nodes that have 'current' as a child
                for parent, children in edges.items():
                    if current in children and parent not in distances:
                        distances[parent] = curr_dist + 1
                        queue.append(parent)

            # Accumulate potential
            exergy = nodes[target]["exergy_score"]
            for node_id, dist in distances.items():
                potential[node_id] += exergy / (float(dist) + 1.0)

        return potential

    def geodesic_descent(
        self,
        start_id: int,
        potential: dict[int, float],
        edges: dict[int, list[int]],
        max_steps: int = 10,
    ) -> list[int]:
        """
        Finds the path of highest gradient of potential (geodesic descent).
        """
        path = [start_id]
        current = start_id
        visited = {start_id}

        for _ in range(max_steps):
            neighbors = edges.get(current, [])
            if not neighbors:
                break

            # Find neighbor with maximum potential
            next_node = None
            max_pot = -1.0

            for neighbor in neighbors:
                if neighbor not in visited:
                    pot = potential.get(neighbor, 0.0)
                    if pot > max_pot:
                        max_pot = pot
                        next_node = neighbor

            if next_node is None or max_pot <= potential.get(current, 0.0):
                # Local maximum reached or no valid neighbors
                break

            current = next_node
            path.append(current)
            visited.add(current)

        return path
