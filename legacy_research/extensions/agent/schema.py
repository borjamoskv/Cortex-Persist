# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Declarative Agent Schema (YAML → Engine).

Re-exports from legacy_research.agents.schema to avoid code duplication.
"""

from legacy_research.agents.schema import (
    AgentRole,
    GuardrailConfig,
    MemoryConfig,
)

__all__ = [
    "AgentRole",
    "GuardrailConfig",
    "MemoryConfig",
]
