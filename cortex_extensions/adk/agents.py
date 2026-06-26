# [C5-REAL] Exergy-Maximized
"""CORTEX ADK Agents - Sovereign AI Agent Definitions.

Re-exports from cortex.adk.agents to avoid code duplication.
"""

from cortex.adk.agents import (
    create_cortex_swarm,
    create_gem_agent,
    create_google_one_agent,
    create_guardian_agent,
    create_memory_agent,
    is_adk_available,
)

__all__ = [
    "create_cortex_swarm",
    "create_gem_agent",
    "create_google_one_agent",
    "create_guardian_agent",
    "create_memory_agent",
    "is_adk_available",
]
