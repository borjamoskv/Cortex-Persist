"""SQLite Graph Algorithms Mixin."""

__all__ = ["SQLiteAlgorithmsMixin"]


class SQLiteAlgorithmsMixin:
    """Mixin for graph algorithm operations."""

    async def find_path(self, source: str, target: str, max_depth: int = 3) -> list:
        """Find paths between entities using BFS."""
        q_ids = "SELECT id, name FROM entities WHERE name IN (?, ?)"
        id_rows = await self._fetch_rows(q_ids, [source, target])
        id_map = {row[1]: row[0] for row in id_rows}

        if source not in id_map or target not in id_map:
            return []

        start_id = id_map[source]
        end_id = id_map[target]
        queue = [(start_id, [])]
        visited = {start_id}

        while queue:
            curr_id, path = queue.pop(0)
            if len(path) >= max_depth:
                continue

            q_neighbors = """SELECT e.id, e.name, er.relation_type, er.weight FROM entity_relations er
                             JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
                             WHERE er.source_entity_id = ? OR er.target_entity_id = ?"""
            neighbors = await self._fetch_rows(q_neighbors, [curr_id, curr_id, curr_id])

            for nid, nname, rtype, weight in neighbors:
                new_step = {
                    "source": source if curr_id == start_id else "intermediate",
                    "target": nname,
                    "type": rtype,
                    "weight": weight,
                }
                if nid == end_id:
                    return path + [new_step]
                if nid not in visited:
                    visited.add(nid)
                    queue.append((nid, path + [new_step]))
        return []

    async def find_context_subgraph(
        self, seed_entities: list, depth: int = 2, max_nodes: int = 50
    ) -> dict:
        """Retrieve a subgraph around seed entities."""
        if not seed_entities:
            return {"nodes": [], "edges": []}
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        visited_ids: set[int] = set()

        placeholders = ",".join(["?"] * len(seed_entities))
        q_init = f"SELECT id, name, entity_type FROM entities WHERE name IN ({placeholders})"
        rows = await self._fetch_rows(q_init, seed_entities)

        current_layer_ids = []
        for eid, name, etype in rows:
            nodes[name] = {"id": eid, "type": etype}
            current_layer_ids.append(eid)
            visited_ids.add(eid)

        for _ in range(depth):
            if not current_layer_ids or len(nodes) >= max_nodes:
                break
            current_layer_ids = await self._expand_subgraph_layer(
                current_layer_ids,
                nodes,
                edges,
                visited_ids,
            )
            if len(nodes) >= max_nodes:
                break
        return {"nodes": [{"name": k, **v} for k, v in nodes.items()], "edges": edges}

    async def _fetch_rows(self, query: str, params: list) -> list:
        """Execute a query and return all rows, handling async/sync branching."""
        if self._is_async:
            async with self.conn.execute(query, params) as cursor:
                return await cursor.fetchall()
        return self.conn.execute(query, params).fetchall()

    async def _expand_subgraph_layer(
        self,
        current_ids: list[int],
        nodes: dict[str, dict],
        edges: list[dict],
        visited_ids: set[int],
    ) -> list[int]:
        """Expand one layer of the subgraph BFS. Returns next layer IDs."""
        phs = ",".join(["?"] * len(current_ids))
        q = f"""SELECT e1.name, e1.entity_type, e1.id, e2.name, e2.entity_type, e2.id, er.relation_type, er.weight
                FROM entity_relations er
                JOIN entities e1 ON er.source_entity_id = e1.id
                JOIN entities e2 ON er.target_entity_id = e2.id
                WHERE er.source_entity_id IN ({phs}) OR er.target_entity_id IN ({phs})"""
        rel_rows = await self._fetch_rows(q, current_ids + current_ids)

        next_ids: list[int] = []
        for s_name, s_type, s_id, t_name, t_type, t_id, r_type, weight in rel_rows:
            self._process_subgraph_node(s_name, s_type, s_id, nodes, visited_ids, next_ids)
            self._process_subgraph_node(t_name, t_type, t_id, nodes, visited_ids, next_ids)

            edge = {"source": s_name, "target": t_name, "type": r_type, "weight": weight}
            if edge not in edges:
                edges.append(edge)
        return next_ids

    def _process_subgraph_node(
        self, name: str, ntype: str, nid: int, nodes: dict, visited: set, next_ids: list
    ) -> None:
        if name in nodes:
            return
        nodes[name] = {"id": nid, "type": ntype}
        if nid not in visited:
            next_ids.append(nid)
            visited.add(nid)
