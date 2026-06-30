# [C5-REAL] Exergy-Maximized
"""Cortex Graph Module.

Entities, Relationships, and Graph Processing.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.graph.backends import GraphBackend, SQLiteBackend
    from babylon60.graph.engine import (
        detect_relationships,
        extract_entities,
        find_path,
        get_backend,
        get_context_subgraph,
        get_graph,
        get_graph_sync,
        process_fact_graph,
        process_fact_graph_sync,
        query_entity,
        query_entity_sync,
    )
    from babylon60.graph.models import Entity, Ghost, Relationship

__all__ = [
    "Entity",
    "Ghost",
    "GraphBackend",
    "Relationship",
    "SQLiteBackend",
    "detect_relationships",
    "extract_entities",
    "find_path",
    "get_backend",
    "get_context_subgraph",
    "get_graph",
    "get_graph_sync",
    "process_fact_graph",
    "process_fact_graph_sync",
    "query_entity",
    "query_entity_sync",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Entity": ("cortex.graph.models", "Entity"),
    "Relationship": ("cortex.graph.models", "Relationship"),
    "Ghost": ("cortex.graph.models", "Ghost"),
    "GraphBackend": ("cortex.graph.backends", "GraphBackend"),
    "SQLiteBackend": ("cortex.graph.backends", "SQLiteBackend"),
    "extract_entities": ("cortex.graph.engine", "extract_entities"),
    "detect_relationships": ("cortex.graph.engine", "detect_relationships"),
    "process_fact_graph": ("cortex.graph.engine", "process_fact_graph"),
    "process_fact_graph_sync": ("cortex.graph.engine", "process_fact_graph_sync"),
    "get_graph": ("cortex.graph.engine", "get_graph"),
    "get_graph_sync": ("cortex.graph.engine", "get_graph_sync"),
    "query_entity": ("cortex.graph.engine", "query_entity"),
    "query_entity_sync": ("cortex.graph.engine", "query_entity_sync"),
    "find_path": ("cortex.graph.engine", "find_path"),
    "get_context_subgraph": ("cortex.graph.engine", "get_context_subgraph"),
    "get_backend": ("cortex.graph.engine", "get_backend"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.graph' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
