# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from legacy_research.graph.backends.base import GraphBackend
    from legacy_research.graph.backends.sqlite import SQLiteBackend

__all__ = ["GraphBackend", "SQLiteBackend", "Neo4jBackend"]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "GraphBackend": ("cortex.graph.backends.base", "GraphBackend"),
    "SQLiteBackend": ("cortex.graph.backends.sqlite", "SQLiteBackend"),
    "Neo4jBackend": ("cortex.graph.backends.neo4j_backend", "Neo4jBackend"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.graph.backends' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
