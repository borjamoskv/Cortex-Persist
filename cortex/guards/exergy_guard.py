"""
CORTEX — Exergy Guard (Axiom Ω₁₃: Thermodynamic Cognition).

Filters incoming facts based on their information density (Exergy) vs raw entropy.
Rejects decorative stochastic output (e.g., apologies, padding, generic AI speak)
that consumes memory without reducing the causal gap.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

logger = logging.getLogger("cortex.guards.exergy")

# Standard stopwords and LLM-isms that consume tokens but provide 0 exergy
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
        "entendido",
        "ciertamente",
        "claro que sí",
        "déjame ayudarte",
        "estoy aquí para",
        "un placer",
        "no dudes en",
        "importante notar",
        "tener en cuenta",
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
    }
)

# Minimum threshold: Below this, the output is considered thermal noise.
# A healthy, concise technical fact usually scores 0.6+
MIN_EXERGY_THRESHOLD = 0.55  # Increased for Aura-Omega rigor (Ω₁₃)


def calculate_shannon_entropy(content: str) -> float:
    """Calculates the character-level Shannon entropy of the string."""
    if not content:
        return 0.0
    probabilities = [v / len(content) for v in Counter(content).values()]
    return -sum(p * math.log2(p) for p in probabilities)


def calculate_repetition_penalty(words: list[str]) -> float:
    """Detects loops and stuttering using Bigram/Trigram overlap."""
    if len(words) < 6:
        return 0.0

    # Check Trigrams
    trigrams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
    counts = Counter(trigrams)
    repeated = sum(v - 1 for v in counts.values() if v > 1)
    # Penalty is the ratio of repeated trigrams to total potential trigrams
    penalty = repeated / len(trigrams)
    # Scale: If 30% of text is trigram repetition, it's likely a loop or very redundant
    return min(penalty * 2.0, 0.8)


def calculate_exergy(content: str) -> float:
    """
    Calculate the thermodynamic exergy (useful work) density of a string.
    Aura-Omega Refinement: Incorporates Shannon Entropy and N-gram Repetition.

    Returns:
        float: 0.0 (pure noise) to 1.0 (pure crystallized information)
    """
    length = len(content)
    if length == 0:
        return 0.0

    lower_content = content.lower()

    # Extract structural words, supporting technical terms (underscore, dash)
    words = re.findall(r"\b[a-záéíóúñ0-9_\-]+\b", lower_content)
    total_words = len(words)

    if total_words < 5:
        return 1.0 if not any(marker in lower_content for marker in _DECORATIVE_MARKERS) else 0.0

    # 1. Semantic Density (Legacy Logic)
    # Stop words now include more common Spanish/English filler.
    semantic_tokens = {w for w in words if w not in _STOP_WORDS and len(w) > 2}
    base_density = len(semantic_tokens) / float(total_words)

    # 2. Shannon Factor: Measures complexity
    # Healthy language has entropy ~3.5 to 5.0.
    entropy = calculate_shannon_entropy(content)
    # Aura-Omega Tuning: Only reward entropy if semantic density is already decent.
    # High entropy with low semantic density = wordy nonsense.
    shannon_factor = min(entropy / 4.0, 1.2) if base_density > 0.4 else 0.7

    # 3. Decorative Penalty (Aesthetic Annihilation)
    # Each marker now subtracts 0.35. We are ruthless vs fluff.
    decorative_penalty = sum(0.35 for marker in _DECORATIVE_MARKERS if marker in lower_content)

    # 4. Repetition Penalty (Aura-Omega)
    rep_penalty = calculate_repetition_penalty(words)

    # Final Composite Score
    total_penalty = min(decorative_penalty + rep_penalty, 0.99)
    exergy = (base_density * shannon_factor) * (1.0 - total_penalty)

    # Shannon-Omega Gate: Pure signal must have high density or face steep decay.
    if exergy < 0.2 or base_density < 0.3:
        return 0.0

    # Reward high-crystallinity facts
    return min(exergy * 1.4, 1.0)


class ExergyGuard:
    """
    Evaluates semantic exergy of incoming facts to ensure they meet Axiom Ω₁₃.
    Decorative payloads without causal utility are aborted.
    """

    def check_thermodynamic_yield(
        self,
        content: str,
        project: str,
        fact_type: str,
        source: str | None = None,
    ) -> float:
        """
        Calculates exergy score and enforces the cutoff threshold.

        Raises:
            ValueError: If the exergy score falls below the minimum viable threshold.
        """
        # Code snippets and JSON have arbitrary syntax, ignore for now to prevent false
        # positives.
        if fact_type not in ("decision", "rule", "note", "analysis", "thought"):
            return 1.0

        score = calculate_exergy(content)

        if score < MIN_EXERGY_THRESHOLD:
            logger.warning(
                "Thermodynamic Violation (Axiom Ω₁₃): Rejected decorative content "
                "(score: %.2f) in project [%s].",
                score,
                project,
            )
            raise ValueError(
                f"[Axiom Ω₁₃] Thermodynamic Violation: Exergy score too low "
                f"({score:.2f} < {MIN_EXERGY_THRESHOLD}). "
                "The text is largely rhetorical, repetitive, or conversational padding. "
                "Strip all conversational markers ('por supuesto', 'aquí tienes', etc) "
                "and submit only crystallized structural facts."
            )

        return score
