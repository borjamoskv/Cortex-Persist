# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - YAML Agent Loader (role.yaml → CortexEngine).

Re-exports from legacy_research.agents.loader to avoid code duplication.
"""

from legacy_research.agents.loader import (
    AgentInstance,
    compile_agent,
    load_agent,
)

__all__ = [
    "AgentInstance",
    "compile_agent",
    "load_agent",
]
