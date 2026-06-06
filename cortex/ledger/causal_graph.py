"""Causal Graph - Trace DAG Extractor.

Extrae subgrafos de ejecución causalmente dependientes para el Rollback Engine.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import aiosqlite


class CausalGraph:
    """DAG de ejecución (node = trace, edge = lineage)."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def compute_affected_subgraph(self, root_event_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Finds all trace nodes causally dependent on root_event_id via BFS."""
        affected = {}
        queue = deque([root_event_id])
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            # Fetch the root event
            cursor = await conn.execute(
                "SELECT * FROM execution_trace_ledger WHERE id = ? AND tenant_id = ?", 
                (root_event_id, tenant_id)
            )
            root_row = await cursor.fetchone()
            if root_row:
                affected[root_event_id] = dict(root_row)
            
            # Walk down the DAG to find dependents
            while queue:
                current_id = queue.popleft()
                
                # Find direct children: lineage contains current_id
                cursor = await conn.execute(
                    "SELECT * FROM execution_trace_ledger WHERE tenant_id = ? AND lineage LIKE ?", 
                    (tenant_id, f'%"{current_id}"%')
                )
                children = await cursor.fetchall()
                for child in children:
                    child_id = child["id"]
                    if child_id not in affected:
                        affected[child_id] = dict(child)
                        queue.append(child_id)
                        
        return list(affected.values())

    async def compute_global_drift(self, window_seconds: int, tenant_id: str = "default") -> float:
        """Calcula el drift termodinámico global (varianza de costos en la ventana)."""
        query = "SELECT cost FROM execution_trace_ledger WHERE tenant_id = ? AND datetime(created_at) >= datetime('now', ?)"
        window_modifier = f"-{window_seconds} seconds"
        
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query, (tenant_id, window_modifier))
            rows = await cursor.fetchall()
            if not rows:
                return 0.0
            costs = [r[0] for r in rows]
            if len(costs) < 2:
                return 0.0
            
            import statistics
            return statistics.variance(costs)

    async def compute_node_risk_scores(self, window_seconds: int, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Calcula el 'permission_to_exist_score' ponderando coste causal e impacto de propagación."""
        query = "SELECT id, cost, lineage FROM execution_trace_ledger WHERE tenant_id = ? AND outcome != 'rolled_back' AND datetime(created_at) >= datetime('now', ?)"
        window_modifier = f"-{window_seconds} seconds"
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, (tenant_id, window_modifier))
            rows = await cursor.fetchall()
            
            import json
            propagation_counts = {}
            nodes = []
            
            for r in rows:
                trace_id = r["id"]
                cost = r["cost"]
                nodes.append({"id": trace_id, "cost": cost})
                
                lineage = json.loads(r["lineage"])
                for parent_id in lineage:
                    propagation_counts[parent_id] = propagation_counts.get(parent_id, 0) + 1
                    
            risk_map = []
            for n in nodes:
                prop = propagation_counts.get(n["id"], 1)  # base propagation 1 to avoid zero risk if leaf
                risk_score = n["cost"] * prop
                
                # Exergy mapping: permission to exist (1.0 = absolute permission, ~0.0 = kill target)
                permission_to_exist = 1.0 / (1.0 + risk_score)
                
                risk_map.append({
                    "id": n["id"],
                    "impact": n["cost"],
                    "propagation": prop,
                    "risk_score": risk_score,
                    "permission_to_exist_score": permission_to_exist
                })
                
            return risk_map

    async def compute_coherence_field(self, window_seconds: int, tenant_id: str = "default") -> float:
        """Calcula el Coherence Field (CF).
        
        CF = 1.0 - (ghost_nodes / total_active_nodes)
        Un ghost node es un nodo activo cuyo linaje incluye un ancestro que fue rolled_back.
        Mide la continuidad ontológica y contradicciones estructurales.
        """
        query_active = "SELECT id, lineage FROM execution_trace_ledger WHERE tenant_id = ? AND outcome != 'rolled_back' AND datetime(created_at) >= datetime('now', ?)"
        query_dead = "SELECT id FROM execution_trace_ledger WHERE tenant_id = ? AND outcome = 'rolled_back'"
        window_modifier = f"-{window_seconds} seconds"
        
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query_active, (tenant_id, window_modifier))
            active_traces = await cursor.fetchall()
            
            if not active_traces:
                return 1.0  # Coherencia perfecta en vacío
                
            cursor = await conn.execute(query_dead, (tenant_id,))
            rolled_back_set = {r[0] for r in await cursor.fetchall()}
            
            if not rolled_back_set:
                return 1.0  # Nadie ha muerto, no hay fantasmas
            
            import json
            contradictions = 0
            for r in active_traces:
                lineage = json.loads(r[1])
                # Incoherencia causal: existes pero tu pasado fue borrado
                if any(p in rolled_back_set for p in lineage):
                    contradictions += 1
                    
            normalized_contradiction = contradictions / len(active_traces)
            return max(0.0, 1.0 - normalized_contradiction)
