# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router — Models & Contracts.

Tipos de datos soberanos: enums, dataclasses y BaseProvider.
Extraído de router.py (Ω₂ Landauer split — 1371 → 5 módulos cohesivos).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

__all__ = [
    "ReasoningMode",
    "IntentProfile",
    "CascadeTier",
    "CascadeEvent",
    "HedgedResult",
    "CortexPrompt",
    "BaseProvider",
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


# ─── Intent Classification ─────────────────────────────────────────────────


class IntentProfile(str, Enum):
    """Clasificación soberana de la intención del prompt.

    Permite al router seleccionar fallbacks con afinidad semántica,
    evitando que el ruido del error se propague entre dominios.
    """

    CODE = "code"
    """Generación, refactoring, debugging o análisis de código."""

    REASONING = "reasoning"
    """Análisis multi-paso, matemáticas, planificación estructurada."""

    CREATIVE = "creative"
    """Escritura, brainstorming, contenido narrativo."""

    ARCHITECT = "architect"
    """Análisis profundo de arquitectura y asedio adversario (Red Team)."""

    GENERAL = "general"
    """Intención genérica o no clasificada — sin restricción de fallback."""

    BELIEF_AUDIT = "belief_audit"
    """Cognitive Handoff: contradiction detection, invariant verification.
    Routes to Auditor Economic (Deep Think) or Premium (Opus)."""

    EPISODIC_PROCESSING = "episodic_processing"
    """Cognitive Handoff: massive context reads, multimodal ingestion.
    Routes to Infrastructure (Gemini 3.1 Pro) for cost-gated prescreen."""


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
    """Representación Soberana de una instrucción para el enjambre.
    Independiente del proveedor final (OpenAI, Anthropic, Gemini, etc).
    """

    system_instruction: str = Field(
        default="You are a helpful assistant.",
        description="El prompt del sistema o rol principal.",
    )
    working_memory: list[dict[str, str]] = Field(
        default_factory=list,
        description="Historial reciente o contexto de trabajo (rol/contenido).",
    )
    episodic_context: list[dict[str, str | None]] = Field(
        default_factory=list,
        description="Recuerdos comprimidos o contexto a largo plazo recuperado.",
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
            "Tipo de intención del prompt. Determina qué fallbacks son "
            "elegibles para el cascade determinista. GENERAL usa todos."
        ),
    )
    reasoning_mode: ReasoningMode | None = Field(
        default=None,
        description="Explicit cognitive mode requiring specific architectural capabilities.",
    )

    def to_openai_messages(self) -> list[dict[str, str]]:
        """Convierte la estructura soberana al formato de mensajes de OpenAI."""
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_instruction}]

        # Inyectar contexto episódico si existe, asimilado tempranamente
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
    """Interfaz estricta que todo proveedor LLM debe cumplir.

    Cada provider declara su `intent_affinity` — el conjunto de intenciones
    que sirve con alta precisión. El router usa esta declaración para
    construir el cascade determinista.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identificador único del proveedor."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo subyacente."""
        ...

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        """Intenciones para las que este provider es adecuado.

        Override en subclases especializadas. Por defecto, GENERAL.
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

    @abstractmethod
    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt y ejecuta la inferencia."""
        ...
