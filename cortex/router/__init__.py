"""CORTEX Router — Deterministic Agent Routing.

Routes pipeline requests to the correct agent(s) based on
intent classification and capability matching.
"""

from cortex.router.router import AgentRouter

__all__ = ["AgentRouter"]
