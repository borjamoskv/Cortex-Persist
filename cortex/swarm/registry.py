"""
cortex/swarm/registry.py - AgentRegistry for Swarm V2.

Design invariants for deterministic replay:
- Iteration order is ALWAYS sorted(agent_id) — never insertion order
- capabilities stored as frozenset for hashability
- register() is idempotent: same agent_id + capabilities = same state
- no mutable global state outside the instance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class RegistryError(Exception):
    """Raised when registry contract is violated."""


@dataclass(frozen=True)
class AgentSpec:
    """
    Immutable agent specification.

    frozen=True ensures the spec is hashable and cannot be mutated
    after registration — critical for deterministic replay.
    """

    agent_id: str
    capabilities: frozenset[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            # sorted list for stable JSON serialization
            "capabilities": sorted(self.capabilities),
        }


class AgentRegistry:
    """
    Registry of agents available to the SwarmRouter.

    Determinism guarantees:
    - Internal store is a plain dict (ordered by insertion, Python 3.7+)
    - ALL iteration is done via sorted(self._agents.keys())
    - register() is idempotent: re-registering same id+caps is a no-op
    - No randomness, timestamps, or external I/O
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}

    def register(
        self,
        agent_id: str,
        capabilities: list[str] | None = None,
    ) -> AgentSpec:
        """
        Register an agent.

        Args:
            agent_id: unique identifier
            capabilities: list of capability strings

        Returns:
            AgentSpec (immutable)

        Raises:
            RegistryError: if agent_id already registered with different caps
        """
        caps = frozenset(capabilities or [])
        spec = AgentSpec(agent_id=agent_id, capabilities=caps)

        if agent_id in self._agents:
            existing = self._agents[agent_id]
            if existing.capabilities != caps:
                raise RegistryError(
                    f"Agent '{agent_id}' already registered with different capabilities. "
                    f"Existing: {sorted(existing.capabilities)}, "
                    f"New: {sorted(caps)}"
                )
            # idempotent: same caps, no-op
            return existing

        self._agents[agent_id] = spec
        return spec

    def get(self, agent_id: str) -> AgentSpec | None:
        """Get agent spec by id."""
        return self._agents.get(agent_id)

    def all(self) -> list[AgentSpec]:
        """
        Return all agents in STABLE SORTED ORDER by agent_id.

        This is the critical invariant for deterministic routing:
        sorted order ensures same input always produces same iteration.
        """
        return [self._agents[k] for k in sorted(self._agents.keys())]

    def agents_with_capability(self, capability: str) -> list[AgentSpec]:
        """
        Return agents that have the given capability, sorted by agent_id.

        Sorted to guarantee deterministic selection order.
        """
        return [
            self._agents[k]
            for k in sorted(self._agents.keys())
            if capability in self._agents[k].capabilities
        ]

    def get_candidates(self, task: str) -> list[AgentSpec]:
        """
        Get list of candidate agents for a given task string.
        Matches task text against capabilities. If no match, returns all.
        """
        task_lower = task.lower()
        candidates = []
        for agent in self.all():
            if any(cap in task_lower for cap in agent.capabilities):
                candidates.append(agent)

        if not candidates:
            return self.all()
        return candidates

    def to_dict(self) -> dict[str, Any]:
        """Stable serialization of registry state (for checksum / replay)."""
        return {"agents": [spec.to_dict() for spec in self.all()]}

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents
