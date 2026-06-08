# [C5-REAL] Exergy-Maximized
"""Neo4j Backend for MÖBIUS OS Graph."""

import os

from neo4j import AsyncGraphDatabase

from cortex.graph.backends.base import GraphBackend


class Neo4jBackend(GraphBackend):
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        await self.driver.close()

    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> str:
        query = """
        MERGE (e:Entity {name: $name, project: $project})
        ON CREATE SET e.entity_type = $entity_type, e.first_seen = $timestamp, e.last_seen = $timestamp, e.mention_count = 1
        ON MATCH SET e.mention_count = e.mention_count + 1, e.last_seen = $timestamp
        RETURN e.name as id
        """
        async with self.driver.session() as session:
            result = await session.run(query, name=name, entity_type=entity_type, project=project, timestamp=timestamp)
            record = await result.single()
            return record["id"] if record else name

    async def upsert_relationship(self, source_id: str, target_id: str, relation_type: str, fact_id: int, timestamp: str) -> str:
        # Dynamic relationship types in Cypher require apoc or direct string formatting (dangerous if unvalidated).
        # We will map it to a generic RELATED_TO and store the relation_type as property, or sanitize it.
        sanitized_rel = relation_type.replace(" ", "_").upper()
        if not sanitized_rel.isalnum() and "_" not in sanitized_rel:
            sanitized_rel = "RELATED_TO"

        query = f"""
        MATCH (s:Entity {{name: $source_id}}), (t:Entity {{name: $target_id}})
        MERGE (s)-[r:{sanitized_rel} {{source_fact_id: $fact_id}}]->(t)
        ON CREATE SET r.weight = 1.0, r.first_seen = $timestamp
        ON MATCH SET r.weight = r.weight + 0.5
        RETURN id(r) as id
        """
        async with self.driver.session() as session:
            result = await session.run(query, source_id=source_id, target_id=target_id, fact_id=fact_id, timestamp=timestamp)
            record = await result.single()
            return str(record["id"]) if record else ""

    async def get_graph(self, project: str | None = None, limit: int = 50) -> dict:
        query = """
        MATCH (s:Entity)-[r]->(t:Entity)
        WHERE ($project IS NULL OR s.project = $project)
        RETURN s.name as source, t.name as target, type(r) as relation, r.weight as weight
        LIMIT $limit
        """
        async with self.driver.session() as session:
            result = await session.run(query, project=project, limit=limit)
            edges = []
            async for record in result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "relation_type": record["relation"],
                    "weight": record["weight"]
                })
            return {"edges": edges}

    async def query_entity(self, name: str, project: str | None = None) -> dict | None:
        query = "MATCH (e:Entity {name: $name}) RETURN e.name as name, e.entity_type as entity_type"
        async with self.driver.session() as session:
            result = await session.run(query, name=name)
            record = await result.single()
            return dict(record) if record else None

    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> str:
        query = """
        MERGE (g:Ghost {reference: $reference, project: $project})
        SET g.context = $context, g.first_seen = $timestamp
        RETURN g.reference as id
        """
        async with self.driver.session() as session:
            result = await session.run(query, reference=reference, context=context, project=project, timestamp=timestamp)
            record = await result.single()
            return record["id"] if record else reference

    async def resolve_ghost(self, ghost_id: str, target_id: str, confidence: float, timestamp: str) -> bool:
        query = """
        MATCH (g:Ghost {reference: $ghost_id}), (e:Entity {name: $target_id})
        MERGE (g)-[r:RESOLVED_TO]->(e)
        SET r.confidence = $confidence, r.resolved_at = $timestamp
        RETURN r
        """
        async with self.driver.session() as session:
            result = await session.run(query, ghost_id=ghost_id, target_id=target_id, confidence=confidence, timestamp=timestamp)
            record = await result.single()
            return record is not None

    async def delete_fact_elements(self, fact_id: int) -> bool:
        query = "MATCH ()-[r {source_fact_id: $fact_id}]->() DELETE r"
        async with self.driver.session() as session:
            await session.run(query, fact_id=fact_id)
            return True

    async def find_path(self, source_name: str, target_name: str, max_depth: int = 3) -> list[dict]:
        query = """
        MATCH p = shortestPath((s:Entity {name: $source_name})-[:*..3]-(t:Entity {name: $target_name}))
        RETURN [n in nodes(p) | n.name] as path
        """
        async with self.driver.session() as session:
            result = await session.run(query, source_name=source_name, target_name=target_name)
            record = await result.single()
            return record["path"] if record else []

    async def find_context_subgraph(self, seed_entities: list[str], depth: int = 2, max_nodes: int = 50) -> dict:
        query = """
        MATCH (s:Entity)-[r]-(t:Entity)
        WHERE s.name IN $seed_entities
        RETURN s.name as source, t.name as target, type(r) as relation
        LIMIT $max_nodes
        """
        async with self.driver.session() as session:
            result = await session.run(query, seed_entities=seed_entities, max_nodes=max_nodes)
            edges = []
            async for record in result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "relation_type": record["relation"]
                })
            return {"edges": edges}
