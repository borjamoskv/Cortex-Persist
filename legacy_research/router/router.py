# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Router - Deterministic Capability Matching.

Maps intents to agent capabilities using keyword/pattern matching
with fallback chain. Deterministic per Ω₁.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from legacy_research.pipeline import ContextPacket

logger = logging.getLogger("cortex.router")


@dataclass
class AgentCapability:
    agent_id: str
    patterns: list[str]
    priority: int = 1
    max_tokens: int = 4096
    cost_per_1k_tokens: float = 0.001
    provider: str = "default"
    description: str = ""


_DEFAULTS: list[AgentCapability] = [
    AgentCapability(
        "security-analyst",
        [r"vulnerab", r"exploit", r"bounty", r"audit.*contract", r"cve-"],
        0,
        8192,
        0.003,
        "anthropic",
    ),
    AgentCapability(
        "code-engineer",
        [r"implement", r"refactor", r"debug", r"build", r"python", r"rust"],
        1,
        4096,
        0.001,
        "gemini",
    ),
    AgentCapability(
        "researcher",
        [r"research", r"analyze", r"compare", r"state.?of.?the.?art"],
        1,
        4096,
        0.001,
        "gemini",
    ),
    AgentCapability(
        "memory-ops",
        [r"remember", r"recall", r"forget", r"persist", r"knowledge"],
        2,
        2048,
        0.0005,
        "default",
    ),
    AgentCapability("general", [r".*"], 99, 4096, 0.001, "gemini"),
]


class AgentRouter:
    """Routes intents to agents via deterministic pattern matching."""

    def __init__(self, capabilities: list[AgentCapability] | None = None):
        self._caps = capabilities or list(_DEFAULTS)
        self._caps.sort(key=lambda c: c.priority)
        self._compiled: list[tuple[AgentCapability, list[re.Pattern]]] = [
            (c, [re.compile(p, re.IGNORECASE) for p in c.patterns]) for c in self._caps
        ]

    def register_agent(self, cap: AgentCapability) -> None:
        self._caps.append(cap)
        self._caps.sort(key=lambda c: c.priority)
        self._compiled = [
            (c, [re.compile(p, re.IGNORECASE) for p in c.patterns]) for c in self._caps
        ]

    def route(
        self,
        intent: str,
        context: ContextPacket | None = None,
        budget_remaining: float = 0.10,
        max_agents: int = 3,
    ) -> dict[str, Any]:
        matches: list[AgentCapability] = []
        for cap, patterns in self._compiled:
            if cap.agent_id == "general":
                continue
            if any(p.search(intent) for p in patterns):
                matches.append(cap)

        if not matches:
            general = next((c for c in self._caps if c.agent_id == "general"), None)
            if general:
                matches = [general]

        # Budget trim
        affordable, remaining = [], budget_remaining
        for cap in matches[:max_agents]:
            est = (cap.max_tokens / 1000) * cap.cost_per_1k_tokens
            if est <= remaining:
                affordable.append(cap)
                remaining -= est
        if not affordable and matches:
            affordable = [matches[0]]

        agents = [c.agent_id for c in affordable]
        est_cost = sum((c.max_tokens / 1000) * c.cost_per_1k_tokens for c in affordable)
        logger.info("🎯 [ROUTER] '%s' → %s (est=$%.4f)", intent[:60], agents, est_cost)
        return {
            "agents": agents,
            "strategy": "sequential" if len(agents) <= 1 else "cascade",
            "max_tokens": max((c.max_tokens for c in affordable), default=4096),
            "estimated_cost": est_cost,
        }
