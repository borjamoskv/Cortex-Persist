# [C5-REAL] Exergy-Maximized
"""
Ultramap / EDG (Epistemic Dependency Graph) Router.
"""

import logging
from typing import Any

from babylon60.database.pool import CortexConnectionPool
from fastapi import APIRouter, Request

logger = logging.getLogger("cortex.routes.ultramap")

router = APIRouter(prefix="/v1/ultramap", tags=["ultramap"])


@router.get("/edg", response_model=dict[str, Any])
async def get_epistemic_dependency_graph(request: Request) -> dict[str, Any]:
    """
    Extracts the Epistemic Dependency Graph (EDG) directly from the C5-REAL SQLite Ledger.
    Searches for 'inject_axiom' actions created by 'autodidact'.
    """
    pool: CortexConnectionPool = request.app.state.pool

    nodes = []
    edges = []

    # Query the Ledger directly
    query = """
        SELECT resource, timestamp, audit_id as hash
        FROM security_audit_log
        WHERE action = 'inject_axiom' AND actor_role = 'autodidact'
        ORDER BY timestamp ASC
    """

    async with pool.acquire() as conn:
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()

            for i, row in enumerate(rows):
                resource_str = row[0]  # e.g. "EDU-001: Adaptive Learning (EDG)"
                timestamp = row[1]
                event_hash = row[2]

                parts = resource_str.split(":", 1)
                node_id = parts[0].strip() if len(parts) > 1 else f"NODE-{i}"
                label = parts[1].strip() if len(parts) > 1 else resource_str

                nodes.append(
                    {"id": node_id, "label": label, "timestamp": timestamp, "hash": event_hash[:8]}
                )

                # Causal edges: link each node to the previous one to simulate a curriculum chain
                if i > 0:
                    prev_resource = rows[i - 1][0]  # type: ignore
                    prev_parts = prev_resource.split(":", 1)
                    prev_id = prev_parts[0].strip() if len(prev_parts) > 1 else f"NODE-{i - 1}"
                    edges.append(
                        {"source": prev_id, "target": node_id, "type": "causal_dependency"}
                    )

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {"total_nodes": len(nodes), "total_edges": len(edges), "state": "C5-REAL"},
    }
