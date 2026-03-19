"""
CORTEX — Pre-LLM Compression Guard (Token Reducer).

Integrates the token-reducer skill mechanics into CORTEX writes.
Validates and compresses text payloads BEFORE they enter the LLM context.
Applies: Format reduction (Layer 0) and Self-Information pruning (Layer 1).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("cortex.guards.compression")

# ---------------------------------------------------------------------------
# Compression Mechanisms (Inherited from token-reducer engine.py)
# ---------------------------------------------------------------------------

FILLER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(basically|essentially|actually|literally|really|very|quite|just)\b", re.I),
    re.compile(r"\b(I think that|It is worth noting that|As you may know|In order to)\b", re.I),
    re.compile(r"\b(please note that|it should be noted that|it is important to)\b", re.I),
    re.compile(r"\b(as a matter of fact|for what it's worth|at the end of the day)\b", re.I),
    re.compile(r"\b(In this regard|With respect to|In terms of|As far as .* is concerned)\b", re.I),
]

WHITESPACE_COLLAPSE = re.compile(r"\s{2,}")

LOW_INFO_WORDS: set[str] = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over",
    "think", "also", "back", "after", "use", "two", "how", "our", "work",
    "first", "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "is", "are", "was", "were", "been", "being",
    "has", "had", "did", "does", "doing", "am",
}

def count_tokens_approx(text: str) -> int:
    """Approximate token count."""
    return int(len(text.split()) * 1.3)

def compress_text(text: str, prune_ratio: float = 0.2) -> tuple[str, dict[str, Any]]:
    """Apply Layer 0 (format) and Layer 1 (prune) to raw text."""
    original_tokens = count_tokens_approx(text)
    
    # Layer 0: Format
    result = text
    for pat in FILLER_PATTERNS:
        result = pat.sub("", result)
    result = WHITESPACE_COLLAPSE.sub(" ", result).strip()
    result = re.sub(r"\n\s*\n+", "\n", result)
    
    # Layer 1: Prune
    words = result.split()
    total = len(words)
    max_removals = int(total * prune_ratio)
    removed = 0
    final_words: list[str] = []

    for w in words:
        clean = re.sub(r"[^\w]", "", w).lower()
        if clean in LOW_INFO_WORDS and removed < max_removals:
            removed += 1
        else:
            final_words.append(w)
            
    compressed = " ".join(final_words)
    compressed_tokens = count_tokens_approx(compressed)
    
    savings = 0.0
    if original_tokens > 0:
        savings = (1 - compressed_tokens / original_tokens) * 100
        
    metrics = {
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "savings_percent": round(savings, 1),
    }
    
    return compressed, metrics

# ---------------------------------------------------------------------------
# The Guard Class
# ---------------------------------------------------------------------------

class CompressionGuard:
    """Pre-LLM guard that intercepts verbose inputs and compresses them."""
    
    def __init__(self, min_length_to_compress: int = 150, prune_ratio: float = 0.2):
        self.min_length = min_length_to_compress
        self.prune_ratio = prune_ratio

    def validate_and_compress(self, content: str) -> str:
        """Compress content if it exceeds the minimum length threshold.
        
        Args:
            content: Raw prompt or text to be processed by LLM.
            
        Returns:
            Compressed text if threshold met, else original text.
        """
        # Exergy check: don't spend compute compressing very short strings
        if len(content) < self.min_length:
            return content
            
        compressed, metrics = compress_text(content, self.prune_ratio)
        
        if metrics["savings_percent"] > 10.0:
            logger.debug(
                "CompressionGuard: Compressed %d -> %d tokens (%.1f%% savings)",
                metrics["original_tokens"],
                metrics["compressed_tokens"],
                metrics["savings_percent"]
            )
            return compressed
            
        return content
