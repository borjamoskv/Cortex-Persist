"""
CORTEX — Exergy Guard (Axiom Ω₁₃: Thermodynamic Cognition).

Filters incoming facts based on their information density (Exergy) vs raw entropy.
Rejects decorative stochastic output (e.g., apologies, padding, generic AI speak)
that consumes memory without reducing the causal gap.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

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
        "procedo a",
        "he actualizado",
        "he implementado",
        "entendido",
    }
)

_STOP_WORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "de", "del", "la", "el",
        "los", "las", "en", "un", "una", "y", "o", "que", "con", "por",
        "para", "se", "es", "no", "al", "su", "más", "como", "pero", "sin",
        "sobre", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "and", "or", "not", "but", "this", "that", "it", "its",
    }
)

# Minimum threshold: Below this, the output is considered thermal noise.
# A healthy, concise technical fact usually scores 0.6+
MIN_EXERGY_THRESHOLD = 0.40


def calculate_exergy(content: str) -> float:
    """
    Calculate the thermodynamic exergy (useful work) density of a string.
    
    Formula:
    Base Entropy = (Unique Semantic Tokens) / (Total Words + 1)
    Penalty = Overlap with decorative stochastic markers.
    Exergy = Base Entropy * (1.0 - Penalty)
    
    Returns:
        float: 0.0 (pure noise) to 1.0 (pure crystallized information)
    """
    length = len(content)
    if length == 0:
        return 0.0
        
    lower_content = content.lower()
    
    # Extract structural words, ignoring boilerplate symbols
    words = re.findall(r"\b[a-záéíóúñ]+\b", lower_content)
    total_words = len(words)
    
    if total_words < 5:
        # Extremely short phrases bypass this filter to allow atomic flags, 
        # unless they are purely decorative.
        return 1.0 if not any(marker in lower_content for marker in _DECORATIVE_MARKERS) else 0.0
        
    semantic_tokens = {w for w in words if w not in _STOP_WORDS and len(w) > 2}
    
    # Base density: how many unique, non-trivial words vs total words
    # If the system repeats itself constantly, this drops.
    base_density = len(semantic_tokens) / float(total_words)
    
    # Calculate penalty based on known LLM low-exergy conversational markers
    penalty = 0.0
    for marker in _DECORATIVE_MARKERS:
        if marker in lower_content:
            # Each decorative phrase drops the exergy by 15%
            penalty += 0.15
            
    # Cap penalty at 0.9 to avoid negative exergy
    penalty = min(penalty, 0.9)
    
    exergy = base_density * (1.0 - penalty)
    
    # Amplify the score non-linearly to reward high density and punish low density.
    # Exergy should drop off a cliff if it starts padding.
    return min(exergy * 1.5, 1.0)


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
        source: Optional[str] = None,
    ) -> float:
        """
        Calculates exergy score and enforces the cutoff threshold.
        
        Raises:
            ValueError: If the exergy score falls below the minimum viable threshold.
        """
        # Code snippets and JSON have arbitrary syntax, ignore for now to prevent false positives.
        # Strict thermodynamic checks apply mostly to natural language decisions, reasoning, and rules.
        if fact_type not in ("decision", "rule", "note", "analysis", "thought"):
            return 1.0
            
        score = calculate_exergy(content)
        
        if score < MIN_EXERGY_THRESHOLD:
            logger.warning(
                "Thermodynamic Violation (Axiom Ω₁₃): Rejected decorative content "
                "(score: %.2f) in project [%s]. Content: %s...",
                score,
                project,
                content[:60].replace("\n", " "),
            )
            raise ValueError(
                f"[Axiom Ω₁₃] Thermodynamic Violation: Exergy score too low ({score:.2f} < {MIN_EXERGY_THRESHOLD}). "
                "The text is largely rhetorical, repetitive, or conversational padding. "
                "Strip all conversational markers ('por supuesto', 'aquí tienes', etc) and submit only crystallized structural facts."
            )
            
        return score
