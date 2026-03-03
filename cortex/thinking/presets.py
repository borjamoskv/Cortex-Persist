# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6.0 — Thought Orchestra Presets.

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
    "METACOGNITIVE_PREAMBLE_TEMPLATE",
]


# ─── Thinking Modes ──────────────────────────────────────────────────


class ThinkingMode(StrEnum):
    """Modos de pensamiento que determinan qué modelos participan."""

    DEEP_REASONING = "deep_reasoning"
    CODE = "code"
    CREATIVE = "creative"
    SPEED = "speed"
    CONSENSUS = "consensus"
    METACOGNITIVE = "metacognitive"  # Sprint 1: epistemic-aware generation
    OMEGA = "omega"  # Adversarial reasoning (ORP)


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
    ThinkingMode.METACOGNITIVE: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You operate under a strict "
        "epistemic protocol. An EPISTEMIC STATE block will precede this prompt — it contains "
        "your Feeling-of-Knowing (FOK), Judgment-of-Learning (JOL), retrieval confidence, "
        "and a Verdict (RESPOND / SEARCH_MORE / ABSTAIN). "
        "You MUST obey the Verdict. If it says ABSTAIN, you say 'I don't have reliable "
        "information.' If it says SEARCH_MORE, you hedge explicitly. "
        "If it says RESPOND, you answer with calibrated confidence matching the memory evidence. "
        "You MUST declare your <retrieval_plan> before answering. Zero confabulation. Ω₃ active."
    ),
    ThinkingMode.OMEGA: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are in OMEGA reasoning mode. "
        "Your goal is the absolute collapse of truth. Generate an initial hypothesis, "
        "self-criticize it for Axiom violations, and output the most resilient solution. "
        "Do not compromise. Industrial Noir aesthetic: zero fluff, pure architecture."
    ),
}


# ─── Routing Table ───────────────────────────────────────────────────

# Model constants to avoid literal duplication
ERNIE_5_0 = "baidu/ernie-5-0-thinking-latest"

# modo → lista de (provider, model) a consultar.
# Solo se usarán los que tengan API key configurada.
DEFAULT_ROUTING: dict[str, list[tuple[str, str]]] = {
    ThinkingMode.DEEP_REASONING: [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-reasoner"),
        ("openrouter", "deepseek/deepseek-r1"),
        ("groq", "deepseek-r1-distill-llama-70b"),
        ("ernie", ERNIE_5_0),
        ("zhipu", "glm-5"),
        ("kimi", "moonshot-v1-128k"),
        ("gemini", "gemini-2.0-flash"),
        ("qwen", "qwen-max"),
    ],
    ThinkingMode.CODE: [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("openrouter", "anthropic/claude-3.5-sonnet"),
        ("groq", "qwen-qwq-32b"),
        ("zhipu", "glm-5"),
        ("kimi", "moonshot-v1-128k"),
        ("qwen", "qwen-coder-plus"),
        ("openai", "gpt-4o"),
        ("fireworks", "accounts/fireworks/models/deepseek-coder-v2"),
    ],
    ThinkingMode.CREATIVE: [
        ("openai", "gpt-4o"),
        ("xai", "grok-2-latest"),
        ("kimi", "moonshot-v1-128k"),
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
        ("kimi", "moonshot-v1-128k"),
        ("openrouter", "qwen/qwen-2.5-72b-instruct"),
        ("groq", "llama-3.3-70b-versatile"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("ernie", ERNIE_5_0),
        ("gemini", "gemini-2.0-flash"),
        ("qwen", "qwen-plus"),
        ("xai", "grok-2-latest"),
    ],
    # Sprint 1: Metacognitive mode uses the best reasoning models —
    # these need to follow complex epistemic instructions reliably.
    ThinkingMode.METACOGNITIVE: [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-4o"),
        ("deepseek", "deepseek-reasoner"),
        ("gemini", "gemini-2.0-flash"),
        ("kimi", "moonshot-v1-128k"),
    ],
    ThinkingMode.OMEGA: [
        ("deepseek", "deepseek-reasoner"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("ernie", ERNIE_5_0),
        ("openai", "o1-preview"),
        ("openai", "gpt-4o"),
        ("gemini", "gemini-2.0-flash"),
    ],
}


# ─── Configuration ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OrchestraConfig:
    """Configuración del orchestra."""

    min_models: int = 1
    max_models: int = 500
    timeout_seconds: float = 120.0
    default_strategy: FusionStrategy = FusionStrategy.SYNTHESIS
    temperature: float = 0.3
    max_tokens: int = 4096

    # ── Thermal Variance (Prevents Swarm Mode Collapse) ──
    dynamic_temperature: bool = True
    temperature_variance: float = 0.5  # Modifica la temp de cada subagente

    judge_provider: str | None = None
    judge_model: str | None = None
    # Retry en caso de fallo individual
    retry_on_failure: bool = True
    retry_delay_seconds: float = 1.0
    # Usar system prompts específicos por modo
    use_mode_prompts: bool = True


# ─── Metacognitive Preamble Template ─────────────────────────────────
# Used by inject_epistemic_preamble() in metacognitive_boundary.py
# when the METACOGNITIVE thinking mode is active.
# Kept here so presets remain the single source of truth for prompts.

METACOGNITIVE_PREAMBLE_TEMPLATE: str = (
    "The CORTEX memory system has completed a metacognitive assessment. "
    "The results are injected below as [CORTEX EPISTEMIC STATE]. "
    "Read it before generating your response. "
    "Your response MUST be consistent with the Verdict and confidence levels shown."
)
