"""SQLite Graph Algorithms Mixin."""

class SQLiteAlgorithmsMixin:
    """Mixin for graph algorithm operations."""

    async def find_path(self, source: str, target: str, max_depth: int = 3) -> list:
        """Find paths between entities using BFS."""
        q_ids = "SELECT id, name FROM entities WHERE name IN (?, ?)"
        if self._is_async:
            async with self.conn.execute(q_ids, (source, target)) as cursor:
                id_map = {row[1]: row[0] for row in await cursor.fetchall()}
        else:
            id_map = {
                row[1]: row[0] for row in self.conn.execute(q_ids, (source, target)).fetchall()
            }

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
            if self._is_async:
                async with self.conn.execute(q_neighbors, (curr_id, curr_id, curr_id)) as cursor:
                    neighbors = await cursor.fetchall()
            else:
                neighbors = self.conn.execute(q_neighbors, (curr_id, curr_id, curr_id)).fetchall()

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
        nodes = {}
        edges = []
        visited_ids = set()

        placeholders = ",".join(["?"] * len(seed_entities))
        q_init = f"SELECT id, name, entity_type FROM entities WHERE name IN ({placeholders})"
        if self._is_async:
            async with self.conn.execute(q_init, seed_entities) as cursor:
                rows = await cursor.fetchall()
        else:
            rows = self.conn.execute(q_init, seed_entities).fetchall()

        current_layer_ids = []
        for row in rows:
            eid, name, etype = row
            nodes[name] = {"id": eid, "type": etype}
            current_layer_ids.append(eid)
            visited_ids.add(eid)

        for _ in range(depth):
            if not current_layer_ids or len(nodes) >= max_nodes:
                break
            phs = ",".join(["?"] * len(current_layer_ids))
            q_expand = f"""SELECT e1.name, e1.entity_type, e1.id, e2.name, e2.entity_type, e2.id, er.relation_type, er.weight
                          FROM entity_relations er
                          JOIN entities e1 ON er.source_entity_id = e1.id
                          JOIN entities e2 ON er.target_entity_id = e2.id
                          WHERE er.source_entity_id IN ({phs}) OR er.target_entity_id IN ({phs})"""
            params = current_layer_ids + current_layer_ids
            if self._is_async:
                async with self.conn.execute(q_expand, params) as cursor:
                    rel_rows = await cursor.fetchall()
            else:
                rel_rows = self.conn.execute(q_expand, params).fetchall()

            next_layer_ids = []
            for s_name, s_type, s_id, t_name, t_type, t_id, r_type, weight in rel_rows:
                if s_name not in nodes:
                    nodes[s_name] = {"id": s_id, "type": s_type}
                    if s_id not in visited_ids:
                        next_layer_ids.append(s_id)
                        visited_ids.add(s_id)
                if t_name not in nodes:
                    nodes[t_name] = {"id": t_id, "type": t_type}
                    if t_id not in visited_ids:
                        next_layer_ids.append(t_id)
                        visited_ids.add(t_id)
                edge = {"source": s_name, "target": t_name, "type": r_type, "weight": weight}
                if edge not in edges:
                    edges.append(edge)
            current_layer_ids = next_layer_ids
            if len(nodes) >= max_nodes:
                break
        return {"nodes": [{"name": k, **v} for k, v in nodes.items()], "edges": edges}
