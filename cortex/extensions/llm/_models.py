# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router - Models & Contracts.

Sovereign data types: enums, dataclasses, and BaseProvider.
Extracted from router.py (Ω₂ Landauer split - 1371 → 5 cohesive modules).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

__all__ = [
    "BaseProvider",
    "CascadeEvent",
    "CascadeTier",
    "CortexPrompt",
    "HedgedResult",
    "IntentProfile",
    "ReasoningMode",
]

# ─── Cognitive Reasoning Modes (Axiom Ω₁₆) ──────────────────────────────


class ReasoningMode(str, Enum):
    """Execution modes that dictate provider selection, hedging, and capability requirements."""

    DEEP_THINK = "deep"
    """Requires mathematical/logical verification. Prioritizes 'reasoner' or 'thinking' models."""

    DEEP_RESEARCH = "deep_research"
    """Requires active tool use, structured searching, and synthesis across domains."""

    ULTRA_THINK = "ultra"
    """P0 Singularity Mode. Demands maximum context, strict zero-hallucination guards,
    and compound problem solving. Overrides all cost gates."""

    DEEPTHINK_R1 = "deepthink_r1"
    """Dedicated DeepSeek-R1 reasoning cluster. Requires native extended chain-of-thought
    capability. Routes exclusively to `deepseek-reasoner` or equivalent R1-class models.
    Used by P0VulnerabilityExtractor for code-level hypothesis generation."""


# ─── Intent Classification ─────────────────────────────────────────────────


class IntentProfile(str, Enum):
    """Sovereign classification of the prompt's intent.

    Allows the router to select fallbacks with semantic affinity,
    preventing error noise from propagating across domains.
    """

    CODE = "code"
    """Code generation, refactoring, debugging, or analysis."""

    REASONING = "reasoning"
    """Multi-step analysis, mathematics, structured planning."""

    CREATIVE = "creative"
    """Writing, brainstorming, narrative content."""

    ARCHITECT = "architect"
    """Deep architecture analysis and adversarial siege (Red Team)."""

    GENERAL = "general"
    """Generic or unclassified intent - no fallback restriction."""

    BELIEF_AUDIT = "belief_audit"
    """Cognitive Handoff: contradiction detection, invariant verification.
    Routes to Auditor Economic (GLM-5.2 Max) or Premium (Opus 4.8 Thinking)."""

    EPISODIC_PROCESSING = "episodic_processing"
    """Cognitive Handoff: massive context reads, multimodal ingestion.
    Routes to Infrastructure (Gemini 3.5 Flash) for cost-gated prescreen."""


class CascadeTier(str, Enum):
    """Classification of which cascade tier resolved the call."""

    PRIMARY = "primary"
    TYPED_MATCH = "typed-match"
    SAFETY_NET = "safety-net"
    NONE = "none"  # all providers failed


@dataclass(frozen=True)
class CascadeEvent:
    """Structured trace for a single execute_resilient call.

    Enables production measurement of entropy delta:
    - typed-match = entropy-neutral (domain preserved)
    - safety-net  = entropy-elevated (domain crossed)
    """

    intent: IntentProfile
    resolved_by: str | None
    tier: CascadeTier
    project: str | None = None
    depth: int = 1  # how many providers attempted before success
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class HedgedResult:
    """Observability payload for hedged request races.

    Captures which provider won, response latency, and which providers
    were cancelled. Essential for tuning hedging_peers configuration.
    """

    winner: str
    """provider_name of the winning provider."""

    response: str
    """Response content from the winner."""

    latency_ms: float
    """Wall-clock latency of the winning provider (ms)."""

    cancelled: tuple[str, ...] = ()
    """provider_names of cancelled (loser) providers."""


# ─── Prompt ────────────────────────────────────────────────────────────────


class CortexPrompt(BaseModel):
    """Sovereign representation of an instruction for the swarm.
    Independent of the final provider (OpenAI, Anthropic, Gemini, etc).
    """

    system_instruction: str = Field(
        default="You are a helpful assistant.",
        description="The system prompt or main role.",
    )
    working_memory: list[dict[str, str]] = Field(
        default_factory=list,
        description="Recent history or working context (role/content).",
    )
    prompt_tokens: int | None = Field(default=None, exclude=True)
    completion_tokens: int | None = Field(default=None, exclude=True)
    episodic_context: list[dict[str, str | None]] = Field(
        default_factory=list,
        description="Compressed memories or retrieved long-term context.",
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    project: str | None = Field(
        default=None,
        description="Project to which this prompt belongs. Used for telemetry and billing.",
    )
    intent: IntentProfile = Field(
        default=IntentProfile.GENERAL,
        description=(
            "Type of prompt intent. Determines which fallbacks are "
            "eligible for the deterministic cascade. GENERAL uses all."
        ),
    )
    reasoning_mode: ReasoningMode | None = Field(
        default=None,
        description="Explicit cognitive mode requiring specific architectural capabilities.",
    )
    swarm_mode: bool = Field(
        default=False,
        description="Ω₂₁: Parallel Swarm Racing. Race multiple providers for O(1) latency.",
    )

    def to_openai_messages(self) -> list[dict[str, str]]:
        """Converts the sovereign structure to the OpenAI messages format."""
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_instruction}]

        # Inject episodic context if it exists, assimilated early
        if self.episodic_context:
            context_str = "\n".join(
                f"[{m.get('role', 'memory')}]: {m.get('content', '')}"
                for m in self.episodic_context
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<episodic_context>\n{context_str}\n</episodic_context>\n"
                        "Use this context for the following interactions if relevant."
                    ),
                }
            )

        messages.extend(self.working_memory)
        return messages


# ─── Provider Interface ────────────────────────────────────────────────────


class BaseProvider(ABC):
    """Strict interface that any LLM provider must fulfill.

    Each provider declares its `intent_affinity` - the set of intents
    it serves with high precision. The router uses this declaration to
    build the deterministic cascade.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the provider."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the underlying model."""
        ...

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        """Intents for which this provider is suitable.

        Override in specialized subclasses. By default, GENERAL.
        """
        return frozenset({IntentProfile.GENERAL})

    @property
    def tier(self) -> str:
        """Provider tier: 'frontier', 'high', or 'local'."""
        return "high"

    @property
    def cost_class(self) -> str:
        """Cost classification: 'free', 'low', 'medium', 'high', 'variable'."""
        return "medium"

    @property
    def context_window(self) -> int:
        """The context window limit of the provider's underlying model (in tokens)."""
        return 128000

    @abstractmethod
    async def invoke(self, prompt: CortexPrompt) -> str:
        """Translates the CortexPrompt and executes the inference."""
        ...
