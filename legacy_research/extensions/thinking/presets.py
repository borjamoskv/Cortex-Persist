# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Thought Orchestra Presets.

Configuración estática del orquestador: modos de pensamiento, prompts de sistema,
tabla de routing por modo, y configuración por defecto.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from legacy_research.extensions.thinking.fusion import FusionStrategy

__all__ = [
    "DEFAULT_ROUTING",
    "METACOGNITIVE_PREAMBLE_TEMPLATE",
    "MODE_SYSTEM_PROMPTS",
    "OrchestraConfig",
    "ThinkingMode",
]


# ─── Thinking Modes ──────────────────────────────────────────────────


class ThinkingMode(str, Enum):
    """Modos de pensamiento que determinan qué modelos participan."""

    DEEP_REASONING = "deep_reasoning"
    CODE = "code"
    CREATIVE = "creative"
    SPEED = "speed"
    CONSENSUS = "consensus"
    METACOGNITIVE = "metacognitive"  # Sprint 1: retrieval-aware generation
    OMEGA = "omega"  # Adversarial reasoning (ORP)
    DEEPTHINK_CLUSTER = "deepthink_cluster"  # DeepSeek-R1 extended reasoning cluster (P0)


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
        "retrieval protocol. An EPISTEMIC STATE block will precede this prompt - it contains "
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
    ThinkingMode.DEEPTHINK_CLUSTER: (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are in DEEPTHINK-R1 cluster mode. "
        "You receive a DiagnosisMatrix (AST analysis: complexity, call graph, dead code, entropy) "
        "and source code. Your task: generate P0 vulnerability hypotheses with surgical precision. "
        "For each finding, output: severity (critical/high/medium/low), vector_type (precision, "
        "reentrancy, access_control, oracle, logic, overflow, race_condition), hypothesis (one "
        "sentence), code_evidence (exact line references), and confidence (C1-C5). "
        "Use extended chain-of-thought to reason through state transitions and invariant violations. "
        "Output valid JSON array. Zero speculation without code evidence. Ω₁ (Byzantine Guard) active."
    ),
}


# ─── Routing Table ───────────────────────────────────────────────────

# Model constants to avoid literal duplication
ERNIE_5_0 = "baidu/ernie-5-0-thinking-latest"
GPT_5_4 = "gpt-5.4"
GPT_5_4_TURBO = "gpt-5.4-turbo"
O3_ULTRA = "o3-ultra-2026"
DEEPSEEK_R1 = "deepseek-r1-2026"
DEEPSEEK_V4 = "deepseek-v4"
GROK_4_1 = "grok-4.1"

# modo → lista de (provider, model) a consultar.
# Solo se usarán los que tengan API key configurada.
DEFAULT_ROUTING: dict[str, list[tuple[str, str]]] = {
    ThinkingMode.DEEP_REASONING: [
        ("ollama", "qwen2.5-coder:7b"),
        ("gemini", "gemini-3.1-pro-preview"),
        ("openai", GPT_5_4),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", DEEPSEEK_R1),
        ("ernie", ERNIE_5_0),
        ("zhipu", "glm-5"),
        ("qwen", "qwen-3.5-397b"),
    ],
    ThinkingMode.CODE: [
        ("ollama", "qwen2.5-coder:7b"),
        ("gemini", "gemini-3.1-pro-preview"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", DEEPSEEK_V4),
        ("zhipu", "glm-5"),
        ("qwen", "qwen-3.5-397b"),
        ("openai", GPT_5_4_TURBO),
        ("fireworks", "accounts/fireworks/models/deepseek-v3"),
    ],
    ThinkingMode.CREATIVE: [
        ("gemini", "gemini-3.1-pro-preview"),
        ("openai", GPT_5_4),
        ("xai", GROK_4_1),
        ("qwen", "qwen-3.5-397b"),
    ],
    ThinkingMode.SPEED: [
        ("venice", "olafangensan-glm-4.7-flash-heretic"),
        ("ollama", "qwen2.5-coder:7b"),
        ("gemini", "gemini-3.1-pro-preview"),
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama-3.3-70b"),
        ("sambanova", "Meta-Llama-3.3-70B-Instruct"),
        ("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct"),
        ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ],
    ThinkingMode.CONSENSUS: [
        ("gemini", "gemini-3.1-pro-preview"),
        ("zhipu", "glm-5"),
        ("openai", GPT_5_4),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", DEEPSEEK_V4),
        ("ernie", ERNIE_5_0),
        ("qwen", "qwen-3.5-397b"),
        ("groq", "llama-3.3-70b-versatile"),
        ("xai", GROK_4_1),
    ],
    # Sprint 1: Metacognitive mode uses the best reasoning models -
    # these need to follow complex retrieval instructions reliably.
    ThinkingMode.METACOGNITIVE: [
        ("gemini", "gemini-3.1-pro-preview"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", GPT_5_4),
        ("deepseek", DEEPSEEK_R1),
    ],
    ThinkingMode.OMEGA: [
        ("venice", "olafangensan-glm-4.7-flash-heretic"),
        ("gemini", "gemini-3.1-pro-preview"),
        ("deepseek", DEEPSEEK_R1),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("ernie", ERNIE_5_0),
        ("openai", O3_ULTRA),
        ("openai", GPT_5_4),
    ],
    # Deepthink Cluster: DeepSeek-R1 primary, reasoning-capable fallbacks only
    ThinkingMode.DEEPTHINK_CLUSTER: [
        ("deepseek", DEEPSEEK_R1),
        ("gemini", "gemini-3.1-pro-preview"),
        ("openai", O3_ULTRA),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("ernie", ERNIE_5_0),
    ],
}


# ─── Configuration ───────────────────────────────────────────────────


@dataclass(frozen=True)
class OrchestraConfig:
    """Configuración del orchestra."""

    min_models: int = 1
    max_models: int = 500
    timeout_seconds: float = 120.0
    default_strategy: FusionStrategy = FusionStrategy.SYNTHESIS
    temperature: float = 0.3
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("CORTEX_LLM_MAX_TOKENS", "4096"))
    )

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
# Used by inject_retrieval_preamble() in metacognitive_boundary.py
# when the METACOGNITIVE thinking mode is active.
# Kept here so presets remain the single source of truth for prompts.

METACOGNITIVE_PREAMBLE_TEMPLATE: str = (
    "[CORTEX EPISTEMIC STATE] follows. It contains Feeling-of-Knowing (FOK), "
    "Judgment-of-Learning (JOL), retrieval confidence, and a binding Verdict "
    "(RESPOND | SEARCH_MORE | ABSTAIN). "
    "Parse it BEFORE generating any output. "
    "Obey the Verdict unconditionally: ABSTAIN → refuse; SEARCH_MORE → hedge explicitly; "
    "RESPOND → answer with calibrated confidence matching the evidence. "
    "Zero confabulation. Ω₃ active."
)
