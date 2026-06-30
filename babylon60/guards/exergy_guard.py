# [C5-REAL] Exergy-Maximized
"""
CORTEX - Exergy Guard (Axiom Ω₁₃: Thermodynamic Cognition).

Filters incoming facts based on their information density (Exergy) vs raw entropy.
Rejects decorative stochastic output (e.g., apologies, padding, generic AI speak)
that consumes memory without reducing the causal gap.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

from babylon60.guards.base import Guard, GuardViolation

logger = logging.getLogger("babylon60.guards.exergy")

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
        "of course",
        "here you go",
        "as an ai language model",
        "hope it is useful",
        "in conclusion",
        "furthermore",
        "here you have",
        "understood",
        "hope this is useful",
        "proceed to explain",
        "helpful to summarize",
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

_ACRONYMS_WHITELIST = frozenset(
    {
        "xml",
        "cnn",
        "ssh",
        "ssl",
        "svg",
        "csv",
        "pdf",
        "sql",
        "txt",
        "db",
        "sh",
        "fs",
        "git",
        "hdc",
        "bft",
        "mcts",
        "dag",
        "ast",
        "pii",
        "wal",
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


def _is_anomalous_word(w: str) -> bool:
    # Ignore pure numbers or pure technical structures (e.g. hex, hashes)
    if w.isdigit() or len(w) <= 2:
        return False
    # If the word is a hexadecimal string or hash prefix, let it pass
    if re.fullmatch(r"[0-9a-f]{6,}", w):
        return False

    # Check vowel/consonant distribution
    vowels = set("aeiouyáéíóú")
    has_vowel = any(c in vowels for c in w)
    if not has_vowel:
        # Allow common acronyms without vowels if short
        if len(w) <= 4 and w in _ACRONYMS_WHITELIST:
            return False
        return True

    # Check consecutive consonants
    consonants_run = 0
    max_consonants_run = 0
    for c in w:
        if c.isalpha() and c not in vowels:
            consonants_run += 1
            max_consonants_run = max(max_consonants_run, consonants_run)
        else:
            consonants_run = 0
    if max_consonants_run >= 5:
        return True

    # Check random letter-number interleaving (e.g., I4Ox, 83rw)
    if re.search(r"[a-z][0-9][a-z]", w) or re.search(r"[0-9][a-z][0-9]", w):
        return True

    return False


def _analyze_letters(letters: list[str]) -> tuple[float, float]:
    """Calculate vowel and rare letter fractions."""
    if not letters:
        return 0.0, 0.0
    vowels_set = set("aeiouyáéíóú")
    rare_set = set("qwkxjz")
    vowel_count = sum(1 for c in letters if c in vowels_set)
    rare_count = sum(1 for c in letters if c in rare_set)
    n = len(letters)
    return vowel_count / n, rare_count / n


def _check_short_phrase(
    words: list[str],
    lower_content: str,
    letters: list[str],
    vowel_fraction: float,
    rare_fraction: float,
) -> float | None:
    """Evaluate short phrases with fewer than 5 words."""
    if len(words) >= 5:
        return None
    if any(_is_anomalous_word(w) for w in words):
        return 0.0
    if letters and vowel_fraction < 0.25:
        # Avoid false positives for technical phrases containing whitelisted acronyms
        has_acronym = any(w in _ACRONYMS_WHITELIST for w in words)
        if not has_acronym:
            return 0.0
    if letters and rare_fraction > 0.15:
        return 0.0
    if any(marker in lower_content for marker in _DECORATIVE_MARKERS):
        return 0.0
    return 1.0


def _check_noise_heuristics(
    content: str,
    letters: list[str],
    vowel_fraction: float,
    rare_fraction: float,
    anomaly_fraction: float,
) -> bool:
    """Evaluate heuristics to filter out random consonant noise, gibberish, or malformed words."""
    if letters and vowel_fraction < 0.25:
        return True
    if letters and rare_fraction > 0.08 and len(content) > 30:
        return True
    if anomaly_fraction > 0.15:
        return True
    return False


def _calculate_semantic_density(words: list[str]) -> float:
    """Calculate the fraction of non-stop-word tokens."""
    if not words:
        return 0.0
    semantic_tokens = {w for w in words if w not in _STOP_WORDS and len(w) > 2}
    return len(semantic_tokens) / float(len(words))


def _calculate_decorative_penalty(lower_content: str) -> float:
    """Sum penalties for decorative conversational markers."""
    return sum(0.35 for marker in _DECORATIVE_MARKERS if marker in lower_content)


def calculate_exergy(content: str) -> float:
    """
    Calculate the thermodynamic exergy (useful work) density of a string.
    Aura-Omega Refinement: Incorporates Shannon Entropy and N-gram Repetition.

    Returns:
        float: 0.0 (pure noise) to 1.0 (pure crystallized information)
    """
    lower_content = content.lower()

    # Extract structural words, supporting technical terms (underscore, dash)
    words = re.findall(r"\b[a-záéíóúñ0-9_\-]+\b", lower_content)
    total_words = len(words)

    if total_words == 0:
        return 0.0

    # Character-level validation
    letters = [c for c in lower_content if c.isalpha()]
    vowel_fraction, rare_fraction = _analyze_letters(letters)

    # Short phrases guard: extremely short valid facts pass with 1.0
    short_phrase_score = _check_short_phrase(
        words, lower_content, letters, vowel_fraction, rare_fraction
    )
    if short_phrase_score is not None:
        return short_phrase_score

    # Heuristic Checks
    anomalous_words = sum(1 for w in words if _is_anomalous_word(w))
    anomaly_fraction = anomalous_words / float(total_words)

    if _check_noise_heuristics(content, letters, vowel_fraction, rare_fraction, anomaly_fraction):
        return 0.0

    # 1. Semantic Density
    base_density = _calculate_semantic_density(words)

    # 2. Shannon Factor: Measures complexity
    entropy = calculate_shannon_entropy(content)
    shannon_factor = min(entropy / 4.0, 1.2) if base_density > 0.4 else 0.7

    # 3. Decorative Penalty
    decorative_penalty = _calculate_decorative_penalty(lower_content)

    # 4. Repetition Penalty
    rep_penalty = calculate_repetition_penalty(words)

    # Final Composite Score
    total_penalty = min(decorative_penalty + rep_penalty + (anomaly_fraction * 2.0), 0.99)
    exergy = (base_density * shannon_factor) * (1.0 - total_penalty)

    # Shannon-Omega Gate: Pure signal must have high density or face steep decay.
    if exergy < 0.2 or base_density < 0.3:
        return 0.0

    # Reward high-crystallinity facts
    return min(exergy * 1.4, 1.0)


class ExergyGuard(Guard[str]):
    """
    Evaluates semantic exergy of incoming facts to ensure they meet Axiom Ω₁₃.
    Decorative payloads without causal utility are aborted.
    """

    def evaluate(
        self,
        payload: str,
        project: str = "",
        fact_type: str = "note",
        source: str | None = None,
        **kwargs,
    ) -> str:
        """
        Calculates exergy score and enforces the cutoff threshold.
        Implementa el Funtor Guard.

        Raises:
            GuardViolation: If the exergy score falls below the minimum viable threshold.
        """
        # Code snippets and JSON have arbitrary syntax, ignore for now to prevent false
        # positives.
        if fact_type not in ("decision", "rule", "note", "analysis", "thought"):
            return payload

        score = calculate_exergy(payload)

        if score < MIN_EXERGY_THRESHOLD:
            logger.warning(
                "Thermodynamic Violation (Axiom Ω₁₃): Rejected decorative content "
                "(score: %.2f) in project [%s].",
                score,
                project,
            )
            raise GuardViolation(
                f"[Axiom Ω₁₃] Thermodynamic Violation: Exergy score too low "
                f"({score:.2f} < {MIN_EXERGY_THRESHOLD}). "
                "The text is largely rhetorical, repetitive, or conversational padding. "
                "Strip all conversational markers ('por supuesto', 'aquí tienes', etc) "
                "and submit only crystallized structural facts."
            )

        return payload


class LandauerGuard(Guard[str]):
    """
    Enforces Axiom Ω₄: Landauer Limit.
    Calculates Shannon Entropy of the payload. For critical facts (sacred axioms),
    requires a minimum bits-per-character density to prevent epistemic limerence.
    Detecta el kernel del homomorfismo textual (OPT-6).
    """

    def evaluate(self, payload: str, is_sacred: bool = False, **kwargs) -> str:
        """
        Validates thermodynamic density.
        Implementa el Funtor Guard.

        Raises:
            GuardViolation: If the Shannon entropy falls below the threshold for a sacred fact.
        """
        entropy = calculate_shannon_entropy(payload)

        # Thresholds: Sacred facts require high density (minimum 4.0 bits/char)
        if is_sacred and entropy < 4.0:
            logger.warning(
                "Landauer Violation (Axiom Ω₄): Rejected low entropy sacred fact (Entropy: %.2f).",
                entropy,
            )
            raise GuardViolation(
                f"[Axiom Ω₄] Landauer Violation: Thermodynamic density too low for Sacred Axiom "
                f"(Entropy: {entropy:.2f} < 4.0). Facts must be highly compressed."
            )

        return payload
