"""CORTEX Agent Runtime — Agent Manifest (Identity + Policy).

The manifest is the runtime contract for an agent. It declares
what the agent can do, what it's allowed to access, and its
operational boundaries. Complements the YAML persona (AgentDefinition).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class AgentManifest:
    """Immutable runtime identity and policy contract.

    This is NOT the YAML persona (AgentDefinition). This is the
    runtime enforcement layer that governs what a running agent
    instance can and cannot do.
    """

    agent_id: str
    purpose: str

    # Tool policy
    tools_allowed: list[str] = field(default_factory=list)

    # Fact access policy
    facts_writable: list[str] = field(default_factory=list)
    facts_readable: list[str] = field(default_factory=list)

    # Escalation
    escalation_targets: list[str] = field(default_factory=list)

    # Trust
    confidence_floor: str = "C3"
    trust_level: str = "C3"

    # Delegation
    can_delegate: bool = False

    # Execution mode
    daemon: bool = False

    # Resource limits
    max_concurrency: int = 1
    budget_tokens: int = 50_000
    budget_usd: float = 5.0
    max_consecutive_errors: int = 3

    # Tenant isolation
    tenant_id: str = "default"
