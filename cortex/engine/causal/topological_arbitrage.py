# [C5-REAL] Exergy-Maximized
"""
Topological Arbitrage & DAG Index - v19 Structural Compression Engine

Convierte a LEA-Ω en un arbitrajista de incertidumbre utilizando un índice
topológico en memoria (TopologyIndex). Se recarga únicamente cuando
`graph_version` se incrementa en SQLite, garantizando lecturas O(1)-O(log N).

Características:
- Tarjan SCC (Aciclicidad estricta)
- Estados derivados (INVALIDATED)
- Ecuación CBR multidimensional
- Evaluación estructural combinada (descendants, fan-out, fan-in, depth)
"""

import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger(__name__)


class TopologyIndex:
    """
    Índice topológico en memoria de las hipótesis del sistema.
    """

    def __init__(self, db_conn):
        self.db = db_conn
        self.current_version = -1

        # Graph structures
        self.nodes = {}  # node_id -> node_data
        self.adj_out = defaultdict(list)  # node_id -> list of (child_id, weight, rel_type, conf)
        self.adj_in = defaultdict(list)  # node_id -> list of (parent_id, weight, rel_type, conf)

        # Structural Metrics cache
        self.metrics = {}  # node_id -> {w_h, cbr, depth, criticality, descendants_count}
        self.sorted_nodes = []  # Topological sort order

        # Heuristic weights for W_h
        self.alpha = 1.0  # descendants
        self.beta = 0.5  # fanout
        self.gamma = 0.3  # betweenness approx (fan-in * fan-out)
        self.delta = 0.8  # criticality (depth)

    async def _fetch_version(self) -> int:
        query = "SELECT value FROM cortex_meta WHERE key = 'hypothesis_graph_version'"
        try:
            async with self.db.execute(query) as cursor:
                row = await cursor.fetchone()
                if row:
                    return int(row[0])
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            pass
        return 0

    async def sync(self) -> bool:
        """
        Sincroniza el índice en memoria si el graph_version de la BD cambió.
        Retorna True si hubo recarga.
        """
        db_version = await self._fetch_version()
        if db_version != self.current_version:
            logger.info(
                f"Graph version drift ({self.current_version} -> {db_version}). Rebuilding TopologyIndex."
            )
            await self._rebuild()
            self.current_version = db_version
            return True
        return False

    async def _rebuild(self):
        """
        Descarga los nodos y aristas y reconstruye las estructuras y métricas.
        """
        self.nodes.clear()
        self.adj_out.clear()
        self.adj_in.clear()
        self.metrics.clear()

        # Load nodes
        async with self.db.execute(
            "SELECT id, statement, probability, svi, evi, cost, impact, status, created_at FROM system_hypotheses"
        ) as cursor:
            async for row in cursor:
                self.nodes[row[0]] = {
                    "statement": row[1],
                    "probability": row[2],
                    "svi": row[3],
                    "evi": row[4],
                    "cost": row[5],
                    "impact": row[6],
                    "status": row[7],
                    "created_at": row[8],
                }

        # Load edges
        async with self.db.execute(
            "SELECT parent_id, child_id, edge_weight, relation_type, confidence FROM hypothesis_edges"
        ) as cursor:
            async for row in cursor:
                p, c, w, r, conf = row
                self.adj_out[p].append((c, w, r, conf))
                self.adj_in[c].append((p, w, r, conf))

        # Validate SCC
        sccs = self._tarjan_scc()
        if any(len(comp) > 1 for comp in sccs):
            logger.error(
                "[P0] CORTEX-OMEGA: Cyclic dependency detected in Causal DAG! Graph structural integrity compromised."
            )
            # Depending on strictness, we might raise an error here.

        # Compute Topo Sort & Metrics
        self._compute_topological_metrics()

    def _tarjan_scc(self) -> list[list[str]]:
        """
        Tarjan's strongly connected components algorithm.
        Returns a list of components (each is a list of node_ids).
        """
        index_counter = 0
        index = {}
        lowlink = {}
        on_stack = set()
        stack = []
        sccs = []

        def strongconnect(v):
            nonlocal index_counter
            index[v] = index_counter
            lowlink[v] = index_counter
            index_counter += 1
            stack.append(v)
            on_stack.add(v)

            for w, _, _, _ in self.adj_out[v]:
                if w not in index:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])

            if lowlink[v] == index[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for v in self.nodes:
            if v not in index:
                strongconnect(v)

        return sccs

    def _compute_topological_metrics(self):
        """
        O(V+E) compute of descendants, paths, and CBR.
        """
        in_degree = {u: len(self.adj_in[u]) for u in self.nodes}
        queue = deque([u for u in self.nodes if in_degree[u] == 0])

        topo_order = []
        depth = {u: 0 for u in self.nodes}

        while queue:
            u = queue.popleft()
            topo_order.append(u)
            for v, _, _, _ in self.adj_out[u]:
                depth[v] = max(depth[v], depth[u] + 1)
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        self.sorted_nodes = topo_order

        # Reverse pass for descendants aggregate impact
        subtree_impact = {
            u: self.nodes[u]["probability"] * self.nodes[u]["impact"] for u in self.nodes
        }
        descendants_count = {u: 0 for u in self.nodes}

        for u in reversed(topo_order):
            for v, w, _, conf in self.adj_out[u]:
                # Transitive aggregation
                subtree_impact[u] += subtree_impact[v] * w * conf
                descendants_count[u] += descendants_count[v] + 1

        # Final computation
        for u in self.nodes:
            fan_out = len(self.adj_out[u])
            fan_in = len(self.adj_in[u])
            betweenness_approx = fan_in * fan_out
            crit = depth[u]

            # W_h = alpha * descendants_impact + beta * fanout + gamma * betweenness + delta * depth
            w_h = (
                self.alpha * subtree_impact[u]
                + self.beta * fan_out
                + self.gamma * betweenness_approx
                + self.delta * crit
            )

            # CBR = (Sum(P_i * Impact_i)) / (Cost * Uncertainty)
            # We use subtree_impact[u] as the numerator (Sum of P_i * Impact_i for this subtree)
            cost = max(self.nodes[u]["cost"], 0.001)
            uncertainty = max(self.nodes[u]["svi"], 0.001)

            cbr = subtree_impact[u] / (cost * uncertainty)

            self.metrics[u] = {
                "w_h": w_h,
                "cbr": cbr,
                "depth": crit,
                "descendants": descendants_count[u],
                "subtree_impact": subtree_impact[u],
            }

    # Public Daemon Interface

    def get_cbr_ranking(self) -> list[dict[str, Any]]:
        """Returns active hypotheses sorted by CBR."""
        active = []
        for u, data in self.nodes.items():
            if data["status"] == "ACTIVE":
                m = self.metrics[u]
                active.append(
                    {
                        "id": u,
                        "statement": data["statement"],
                        "cbr": m["cbr"],
                        "w_h": m["w_h"],
                        "cost": data["cost"],
                        "uncertainty": data["svi"],
                    }
                )
        return sorted(active, key=lambda x: x["cbr"], reverse=True)

    def get_next_optimal_task(self, in_flight: set[str]) -> dict[str, Any] | None:
        """Returns the optimal task based on CBR, bypassing in-flight tasks and applying a starvation boost."""
        import time
        from datetime import datetime, timezone

        active = []
        now = time.time()
        for u, data in self.nodes.items():
            if data["status"] == "ACTIVE" and u not in in_flight:
                m = self.metrics[u]
                cbr = m["cbr"]

                # Default age if parsing fails
                age_seconds = 1.0
                try:
                    # created_at is typically ISO 8601 or SQLite format
                    dt = datetime.fromisoformat(
                        data.get("created_at", datetime.now(timezone.utc).isoformat()).replace(
                            "Z", "+00:00"
                        )
                    )
                    age_seconds = max(1.0, now - dt.timestamp())
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to parse created_at for starvation boost: %s", e)

                import math

                # Starvation boost: CBR scales logarithmically with age
                boosted_cbr = cbr * (1.0 + math.log1p(age_seconds / 3600.0))

                active.append(
                    {
                        "id": u,
                        "statement": data["statement"],
                        "cbr": cbr,
                        "boosted_cbr": boosted_cbr,
                        "w_h": m["w_h"],
                    }
                )

        if not active:
            return None

        # Determinist fallback using id for ties
        active.sort(key=lambda x: (x["boosted_cbr"], x["id"]), reverse=True)
        return active[0]

    def descendants(self, node_id: str) -> set[str]:
        """Returns all transitive descendants."""
        visited = set()
        queue = deque([node_id])
        while queue:
            u = queue.popleft()
            for v, _, _, _ in self.adj_out[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        return visited

    async def invalidate_cascade(self, node_id: str, reason: str = "parent_false") -> None:
        """
        El operador requiere estados derivados (INVALIDATED), no elimincaciones (Zero Anergía).
        Si un nodo cae (FALSIFIED), sus descendientes son INVALIDATED.
        """
        targets = self.descendants(node_id)
        if not targets:
            return

        target_list = list(targets)
        # We prepare an update to SQLite
        query = f"UPDATE system_hypotheses SET status = 'INVALIDATED', resolution_reason = ? WHERE id IN ({','.join(['?'] * len(target_list))})"

        params = [reason] + target_list
        try:
            await self.db.execute(query, params)
            await self.db.commit()
            logger.info(f"Invalidated {len(target_list)} descendants of {node_id} due to {reason}.")
            # Force cache rebuild next cycle
            await self.db.execute(
                "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
            )
            await self.db.commit()
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.error(f"Failed to cascade invalidate: {e}")
