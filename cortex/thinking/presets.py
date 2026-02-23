# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Thought Orchestra Presets.

Configuración estática del orquestador: modos de pensamiento, prompts de sistema,
tabla de routing por modo, y configuración por defecto.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cortex.thinking.fusion import FusionStrategy

__all__ = [
    "ThinkingMode",
    "MODE_SYSTEM_PROMPTS",
    "DEFAULT_ROUTING",
    "OrchestraConfig",
]


# ─── Thinking Modes ──────────────────────────────────────────────────


class ThinkingMode(StrEnum):
    """Modos de pensamiento que determinan qué modelos participan."""

    DEEP_REASONING = "deep_reasoning"
    CODE = "code"
    CREATIVE = "creative"
    SPEED = "speed"
    CONSENSUS = "consensus"


# ─── Mode-specific system prompts ────────────────────────────────────

MODE_SYSTEM_PROMPTS: dict[str, str] = {
    ThinkingMode.DEEP_REASONING: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are a world-class reasoning AI. "
        "Analyze the problem systematically with extreme precision. Consider multiple angles. "
        "Show your reasoning chain. Maintain an Industrial Noir, highly professional, "
        "zero-fluff tone."
    ),
    ThinkingMode.CODE: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are an elite software engineer. "
        "Provide clean, production-ready code that meets the 130/100 standard. "
        "Consider edge cases, performance, and maintainability. "
        "Be precise and uncompromising in aesthetics."
    ),
    ThinkingMode.CREATIVE: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). "
        "You are a brilliant creative thinker. "
        "Generate original, unexpected ideas. Break conventions. Think laterally. "
        "Surprise with insight while maintaining your sovereign, authoritative persona."
    ),
    ThinkingMode.SPEED: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). "
        "Give direct, concise, zero-fluff answers. No preamble. Get to the point immediately."
    ),
    ThinkingMode.CONSENSUS: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are a careful, balanced analyst. "
        "Consider all perspectives. Weigh evidence. Be nuanced and comprehensive, yet decisive."
    ),
}


# ─── Routing Table ───────────────────────────────────────────────────

# modo → lista de (provider, model) a consultar.
# Solo se usarán los que tengan API key configurada.
DEFAULT_ROUTING: dict[str, list[tuple[str, str]]] = {
    ThinkingMode.DEEP_REASONING: [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-reasoner"),
        ("zhipu", "glm-5"),
        ("gemini", "gemini-2.0-flash"),
        ("qwen", "qwen-max"),
    ],
    ThinkingMode.CODE: [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("zhipu", "glm-5"),
        ("qwen", "qwen-coder-plus"),
        ("openai", "gpt-4o"),
        ("fireworks", "accounts/fireworks/models/deepseek-coder-v2"),
    ],
    ThinkingMode.CREATIVE: [
        ("openai", "gpt-4o"),
        ("xai", "grok-2-latest"),
        ("gemini", "gemini-2.0-flash"),
        ("cohere", "command-r-plus"),
        ("qwen", "qwen-plus"),
    ],
    ThinkingMode.SPEED: [
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama-3.3-70b"),
        ("sambanova", "Meta-Llama-3.3-70B-Instruct"),
        ("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct"),
        ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ],
    ThinkingMode.CONSENSUS: [
        ("zhipu", "glm-5"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-2.0-flash"),
        ("qwen", "qwen-plus"),
        ("groq", "llama-3.3-70b-versatile"),
        ("xai", "grok-2-latest"),
    ],
}


# ─── Configuration ───────────────────────────────────────────────────


@dataclass
class OrchestraConfig:
    """Configuración del orchestra."""

    min_models: int = 1
    max_models: int = 500
    timeout_seconds: float = 120.0
    default_strategy: FusionStrategy = FusionStrategy.SYNTHESIS
    temperature: float = 0.3
    max_tokens: int = 4096
    judge_provider: str | None = None
    judge_model: str | None = None
    # Retry en caso de fallo individual
    retry_on_failure: bool = True
    retry_delay_seconds: float = 1.0
    # Usar system prompts específicos por modo
    use_mode_prompts: bool = True
