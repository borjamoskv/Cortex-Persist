from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SalienceCandidate:
    """Pure data contract between graph layer and router."""
    agent_id: str
    region: str
    network: str          # DMN | CEN | SN
    salience: float       # 0.0 – 1.0, from Neo4j BrainRegion.activation
    latency_ms: float     # from CONNECTS_TO.latency_ms

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "region": self.region,
            "network": self.network,
            "salience": self.salience,
            "latency_ms": self.latency_ms,
        }


@runtime_checkable
class GraphSource(Protocol):
    def get_candidates(self, task: str) -> list[SalienceCandidate]:
        ...


class SNGraphSource:
    """
    Queries the Salience Network (SN) subgraph in Neo4j and returns
    BrainRegion nodes as SalienceCandidates, sorted deterministically
    by (salience DESC, agent_id ASC) so routing is pure.
    """

    # Cypher: fetch SN nodes with their best outbound latency
    _QUERY = """
        MATCH (r:BrainRegion {network: 'SN'})
        OPTIONAL MATCH (r)-[c:CONNECTS_TO]->()
        WITH r, min(c.latency_ms) AS min_lat
        RETURN
            r.region_id   AS region_id,
            r.name        AS name,
            r.activation  AS activation,
            coalesce(min_lat, 0.0) AS latency_ms
        ORDER BY r.activation DESC, r.region_id ASC
    """

    def __init__(self, driver):
        """
        driver: neo4j.GraphDatabase.driver instance.
        Injected so the source remains testable without a live DB.
        """
        self._driver = driver

    def get_candidates(self, task: str) -> list[SalienceCandidate]:
        with self._driver.session() as session:
            result = session.run(self._QUERY)
            candidates = [
                SalienceCandidate(
                    agent_id=row["region_id"],
                    region=row["name"],
                    network="SN",
                    salience=float(row["activation"] or 0.0),
                    latency_ms=float(row["latency_ms"] or 0.0),
                )
                for row in result
            ]
        # Deterministic sort: salience desc, agent_id asc (tiebreak)
        return sorted(candidates, key=lambda c: (-c.salience, c.agent_id))


class MockSNGraphSource:
    """Deterministic stub for tests — no Neo4j required."""

    def __init__(self, candidates: list[SalienceCandidate]):
        self._candidates = sorted(candidates, key=lambda c: (-c.salience, c.agent_id))

    def get_candidates(self, task: str) -> list[SalienceCandidate]:
        return copy.deepcopy(self._candidates)
