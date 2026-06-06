from typing import Protocol, List, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class IntentVector:
    semantic_vector: np.ndarray | list[float]
    task_vector: np.ndarray | list[float]
    temporal_bias: float
    abstraction_level: float


@dataclass
class MemoryNode:
    id: str
    embedding: np.ndarray | list[float]
    fact_type: str
    timestamp: float
    causal_links: list[str] = field(default_factory=list)
    semantic_tags: list[str] = field(default_factory=list)
    content: str = ""  # Populated ONLY during late hydration phase


@dataclass
class MemorySubgraph:
    root_query: str
    nodes: list[MemoryNode]
    edges: list[tuple[str, str, float]]
    coherence_score: float


class MemoryProvider(Protocol):
    def embed(self, text: str) -> np.ndarray | list[float]: ...

    def search(self, query: str, limit: int = 10) -> list[MemoryNode]: ...

    def vector_search(
        self, embedding: np.ndarray | list[float], limit: int = 50
    ) -> list[MemoryNode]: ...

    def neighbors(self, node_id: str) -> list[MemoryNode]: ...

    def causal_edges(self, node_id: str) -> list[tuple[str, str, float]]: ...

    def hydrate(self, nodes: list[MemoryNode]) -> list[MemoryNode]: ...
