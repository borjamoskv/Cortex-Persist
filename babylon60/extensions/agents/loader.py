# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - YAML Agent Loader (role.yaml → CortexEngine).

Re-exports from babylon60.agents.loader to avoid code duplication.
"""

from babylon60.agents.loader import (
    AgentInstance,
    compile_agent,
    load_agent,
)

__all__ = [
    "AgentInstance",
    "compile_agent",
    "load_agent",
]
