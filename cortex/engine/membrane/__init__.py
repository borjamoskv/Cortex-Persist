"""
CORTEX v8.2.0 — Sovereign Membrane (OAXACA-1).

The unified O(1) admission gate for CORTEX. Consolidates semantic density (Exergy)
with behavioral telemetry (Thermodynamic Counters) into a single sovereign filter.

Axioms:
- Ω₁ (Byzantine Law): Trust no stochastic output until verified.
- Ω₂ (Thermodynamic Law): Noise is the enemy of intelligence.
- Ω₃ (The Cycle): Forced friction purifies the signal.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .models import MembraneLog, MembraneLogLevel, PureEngram
from .sanitizer import SovereignSanitizer

logger = logging.getLogger("cortex.membrane")

# --- Semantic Constants ---
_DECORATIVE_MARKERS = frozenset(
    {
        "por supuesto",
        "aquí tienes",
        "como un modelo de lenguaje",
        "espero que te sea útil",
        "es importante notar",
        "en conclusión",
        "en resumen",
        "sin embargo",
        "además",
        "procedo a",
        "he actualizado",
        "he implementado",
        "entendido",
    }
)

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "en",
        "un",
        "una",
        "y",
        "o",
        "que",
        "con",
        "por",
        "para",
        "se",
        "es",
        "no",
        "al",
        "su",
        "más",
        "como",
        "pero",
        "sin",
        "sobre",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "and",
        "or",
        "not",
        "but",
        "this",
        "that",
        "it",
        "its",
        "i",
        "me",
        "my",
        "you",
        "your",
        "he",
        "she",
        "we",
        "they",
        "now",
        "just",
        "very",
        "too",
        "also",
        "well",
        "how",
        "why",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "these",
        "those",
    }
)


class MembraneState(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DECORATIVE = "decorative"
    QUARANTINED = "quarantined"


class Action(str, Enum):
    ADMIT = "admit"
    DEGRADE = "degrade"
    REJECT = "reject"
    CAUTERIZE = "cauterize"


@dataclass
class Diagnostic:
    exergy_score: float
    behavioral_score: float
    state: MembraneState
    reasons: list[str]


@dataclass
class AdmitResult:
    action: Action
    diagnostic: Diagnostic
    metadata_patch: dict[str, Any] | None = None


class SovereignMembrane:
    """
    The O(1) entry point for cognitive induction.
    Enforces the 'OAXACA' threshold.
    """

    def __init__(
        self,
        exergy_threshold: float = 0.40,
        min_density: int = 10,
        max_tool_fails: int = 3,
        max_stale_reads: int = 5,
    ):
        self.exergy_threshold = exergy_threshold
        self.min_density = min_density
        self.max_tool_fails = max_tool_fails
        self.max_stale_reads = max_stale_reads
        self.sanitizer = SovereignSanitizer()

    def calculate_exergy(self, content: str) -> float:
        """Calculate semantic information density."""
        return calculate_exergy(content)

    def evaluate(
        self,
        content: str,
        fact_type: str,
        counters: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdmitResult:
        """
        Perform O(1) triage on a memory induction proposal.
        """
        reasons = []
        c = counters or {}

        # 1. Physical Density (Thalamus Gate)
        if len(content.strip()) < self.min_density:
            reasons.append("low_physical_density")
            return AdmitResult(Action.REJECT, Diagnostic(0.0, 1.0, MembraneState.ACTIVE, reasons))

        # 2. Semantic Exergy (Exergy Guard)
        exergy_score = 1.0
        if fact_type in ("decision", "rule", "note", "analysis", "thought"):
            exergy_score = self.calculate_exergy(content)
            if exergy_score < self.exergy_threshold:
                reasons.append(f"low_exergy_score:{exergy_score:.2f}")

        # 3. Behavioral Telemetry (Thermodynamic Counters)
        behavioral_score = 1.0
        if c.get("consecutive_tool_fails", 0) >= self.max_tool_fails:
            behavioral_score *= 0.5
            reasons.append("high_tool_failure_rate")

        if c.get("file_reads_without_delta", 0) >= self.max_stale_reads:
            behavioral_score *= 0.5
            reasons.append("stale_context_expansion")

        # 4. State Determination
        state = MembraneState.ACTIVE
        action = Action.ADMIT

        if "low_exergy_score" in "".join(reasons) and behavioral_score < 1.0:
            # Dangerous combination: low quality + loop behavior
            state = MembraneState.QUARANTINED
            action = Action.REJECT
            reasons.append("membrane_breach_detected")
        elif exergy_score < self.exergy_threshold or behavioral_score < 1.0:
            state = MembraneState.DECORATIVE
            action = Action.DEGRADE
            reasons.append("degrading_to_decorative")

        if action != Action.ADMIT:
            logger.warning(
                "⍲ Membrane: %s | Exergy: %.4f | Behavior: %.4f | Reasons: %s",
                action.upper(),
                exergy_score,
                behavioral_score,
                ", ".join(reasons),
            )

        return AdmitResult(
            action,
            Diagnostic(exergy_score, behavioral_score, state, reasons),
            metadata_patch={"membrane_state": state.value, "exergy": exergy_score},
        )


def calculate_exergy(content: str) -> float:
    """Calculates the exergy (useful work) of a content string.
    Axiom Ω2: More tokens != more intelligence.
    """
    if not content or not isinstance(content, str):
        return 0.0
    stripped = content.strip()
    if not stripped:
        return 0.0

    lower_content = stripped.lower()
    words = re.findall(r"\b[a-záéíóúñ]+\b", lower_content)
    total_words = len(words)

    if total_words < 5:
        return 1.0 if not any(m in lower_content for m in _DECORATIVE_MARKERS) else 0.0

    semantic_tokens = {w for w in words if w not in _STOP_WORDS and len(w) > 2}
    base_density = len(semantic_tokens) / float(total_words)

    penalty = sum(0.15 for marker in _DECORATIVE_MARKERS if marker in lower_content)
    exergy = base_density * (1.0 - min(penalty, 0.9))

    # Bonus for structural markers (code, lists, headers)
    structural_bonus = 0.2 if any(m in stripped for m in ("```", "###", "1.", "- ")) else 0.0

    exergy = exergy + structural_bonus
    return float(max(0.1, min(1.0, exergy)))


__all__ = [
    "SovereignMembrane",
    "AdmitResult",
    "Action",
    "MembraneState",
    "calculate_exergy",
    "Diagnostic",
    "SovereignSanitizer",
    "PureEngram",
    "MembraneLog",
    "MembraneLogLevel",
]
