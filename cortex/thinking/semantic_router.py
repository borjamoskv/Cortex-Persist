# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Semantic Router (KETER-∞ Ola 3).

Zero-conceptual semantic routing: analyzes prompt content and automatically
selects the optimal ThinkingMode instead of requiring manual selection.

Architecture::

    prompt → SemanticRouter.classify() → ThinkingMode
                ↓
        Keyword density   (fast, O(n) tokenization)
        Code detection    (regex-based heuristics)
        Intent signals    (question patterns, creative triggers)

The router is deliberately lightweight (no LLM call, no embedding).
It operates in <1ms for any prompt length.

Usage::

    router = SemanticRouter()
    mode = router.classify("Fix the bug in auth.py where tokens expire")
    # → ThinkingMode.CODE

    mode = router.classify("What's the root cause of the OOM?")
    # → ThinkingMode.DEEP_REASONING
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from cortex.thinking.presets import ThinkingMode

__all__ = ["SemanticRouter", "RouteDecision"]

logger = logging.getLogger("cortex.thinking.semantic_router")


# ─── Signal Sets ────────────────────────────────────────────────────

_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".rs",
        ".go",
        ".java",
        ".swift",
        ".kt",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".sh",
        ".sql",
        ".html",
        ".css",
        ".vue",
        ".svelte",
    }
)

_CODE_KEYWORDS = frozenset(
    {
        "function",
        "class",
        "import",
        "def",
        "return",
        "async",
        "await",
        "const",
        "let",
        "var",
        "struct",
        "enum",
        "interface",
        "type",
        "bug",
        "error",
        "traceback",
        "exception",
        "stacktrace",
        "debug",
        "refactor",
        "test",
        "unittest",
        "pytest",
        "fixture",
        "api",
        "endpoint",
        "middleware",
        "router",
        "handler",
        "database",
        "query",
        "migration",
        "schema",
        "orm",
        "deploy",
        "docker",
        "kubernetes",
        "ci",
        "cd",
        "pipeline",
        "lint",
        "format",
        "mypy",
        "ruff",
        "eslint",
        "prettier",
        "git",
        "merge",
        "rebase",
        "branch",
        "commit",
        "pr",
        "corregir",
        "arreglar",
        "implementar",
        "refactorizar",
    }
)

_CREATIVE_KEYWORDS = frozenset(
    {
        "idea",
        "brainstorm",
        "imagine",
        "creative",
        "design",
        "brand",
        "name",
        "naming",
        "story",
        "narrative",
        "concept",
        "vision",
        "innovate",
        "invent",
        "explore",
        "alternative",
        "what if",
        "genera",
        "inventa",
        "imagina",
        "diseña",
        "crea",
        "piensa",
    }
)

_REASONING_KEYWORDS = frozenset(
    {
        "why",
        "because",
        "reason",
        "cause",
        "root",
        "analyze",
        "analysis",
        "explain",
        "understand",
        "compare",
        "tradeoff",
        "trade-off",
        "architecture",
        "decision",
        "strategy",
        "approach",
        "evaluate",
        "pros",
        "cons",
        "implications",
        "consequences",
        "impact",
        "por qué",
        "analiza",
        "explica",
        "compara",
        "evalúa",
    }
)

_SPEED_PATTERNS = re.compile(
    r"^(yes|no|true|false|which|what is|cuál|qué es|define|list|translate|traduce)",
    re.IGNORECASE,
)

_CODE_FILE_RE = re.compile(
    r"\b\w+\.(?:py|js|ts|tsx|jsx|rs|go|java|swift|kt|c|cpp|h|rb|sh|sql|html|css)\b"
)

_CODE_BLOCK_RE = re.compile(r"```\w*\n")

_CODE_PATTERN_RE = re.compile(
    r"(?:def |class |import |from .+ import|function |const |let |var |=> |\(\) ->)"
)


# ─── Data Models ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Result of semantic classification."""

    mode: ThinkingMode
    confidence: float  # 0.0-1.0
    signals: dict[str, float] = field(default_factory=dict)
    reason: str = ""

    def __repr__(self) -> str:
        return f"RouteDecision({self.mode.value}, conf={self.confidence:.2f})"


# ─── Semantic Router ─────────────────────────────────────────────────


class SemanticRouter:
    """Classifies prompts into ThinkingMode using lightweight heuristics.

    No LLM calls, no embeddings. Pure signal analysis in O(n).
    """

    def __init__(
        self,
        *,
        code_threshold: float = 0.3,
        creative_threshold: float = 0.25,
        reasoning_threshold: float = 0.2,
    ):
        self._code_threshold = code_threshold
        self._creative_threshold = creative_threshold
        self._reasoning_threshold = reasoning_threshold

    def classify(self, prompt: str) -> RouteDecision:
        """Classify a prompt into the optimal ThinkingMode.

        Returns RouteDecision with mode, confidence, and signal breakdown.
        """
        if not prompt or not prompt.strip():
            return RouteDecision(
                mode=ThinkingMode.SPEED,
                confidence=0.5,
                reason="empty prompt → speed fallback",
            )

        signals = self._extract_signals(prompt)
        mode, confidence, reason = self._decide(signals)

        decision = RouteDecision(
            mode=mode,
            confidence=round(confidence, 3),
            signals=signals,
            reason=reason,
        )

        logger.debug("SemanticRouter: %s → %s (%s)", prompt[:50], decision.mode.value, reason)
        return decision

    def classify_batch(self, prompts: list[str]) -> list[RouteDecision]:
        """Classify multiple prompts."""
        return [self.classify(p) for p in prompts]

    # ── Signal Extraction ────────────────────────────────────────

    def _extract_signals(self, prompt: str) -> dict[str, float]:
        """Extract all signal dimensions from the prompt."""
        lower = prompt.lower()
        words = set(re.findall(r"\b\w+\b", lower))
        word_count = max(len(words), 1)

        # Code signals
        code_keyword_hits = len(words & _CODE_KEYWORDS)
        code_file_hits = len(_CODE_FILE_RE.findall(prompt))
        code_block_hits = len(_CODE_BLOCK_RE.findall(prompt))
        code_pattern_hits = len(_CODE_PATTERN_RE.findall(prompt))
        code_score = min(
            1.0,
            (
                (code_keyword_hits / word_count) * 2.0
                + (code_file_hits * 0.3)
                + (code_block_hits * 0.4)
                + (code_pattern_hits * 0.3)
            ),
        )

        # Creative signals
        creative_hits = len(words & _CREATIVE_KEYWORDS)
        creative_score = min(1.0, (creative_hits / word_count) * 3.0)

        # Reasoning signals
        reasoning_hits = len(words & _REASONING_KEYWORDS)
        reasoning_score = min(1.0, (reasoning_hits / word_count) * 3.0)

        # Speed signals (short prompts, direct questions)
        is_short = len(prompt.split()) <= 8
        is_speed_pattern = bool(_SPEED_PATTERNS.match(prompt.strip()))
        speed_score = 0.0
        if is_short and is_speed_pattern:
            speed_score = 0.8
        elif is_short:
            speed_score = 0.4
        elif is_speed_pattern:
            speed_score = 0.3

        # Length penalty: very long prompts → reasoning
        length_boost = min(0.2, len(prompt) / 5000)

        return {
            "code": round(code_score, 3),
            "creative": round(creative_score, 3),
            "reasoning": round(reasoning_score + length_boost, 3),
            "speed": round(speed_score, 3),
        }

    # ── Decision Logic ───────────────────────────────────────────

    def _decide(self, signals: dict[str, float]) -> tuple[ThinkingMode, float, str]:
        """Select mode from signals using threshold-based priority."""
        code = signals["code"]
        creative = signals["creative"]
        reasoning = signals["reasoning"]
        speed = signals["speed"]

        # Priority: Code > Creative > Reasoning > Speed > Default
        if code >= self._code_threshold and code >= creative and code >= reasoning:
            return ThinkingMode.CODE, min(1.0, 0.5 + code), f"code signals: {code:.2f}"

        if creative >= self._creative_threshold and creative > reasoning:
            return (
                ThinkingMode.CREATIVE,
                min(1.0, 0.5 + creative),
                f"creative signals: {creative:.2f}",
            )

        if reasoning >= self._reasoning_threshold:
            return (
                ThinkingMode.DEEP_REASONING,
                min(1.0, 0.5 + reasoning),
                f"reasoning signals: {reasoning:.2f}",
            )

        if speed >= 0.5:
            return ThinkingMode.SPEED, min(1.0, 0.4 + speed), f"speed signals: {speed:.2f}"

        # Default: deep reasoning (safest fallback)
        return ThinkingMode.DEEP_REASONING, 0.5, "no dominant signal → deep reasoning"
