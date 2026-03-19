"""
Haiku Guard (Ω₄): Aesthetic Integrity Validator for Sacred Truths.
Enforces the 5-7-5 syllable structure for facts with high exergy or sacred intent.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from cortex.immune.types import GuardViolation

logger = logging.getLogger("cortex.immunity.haiku")


def count_syllables_es(word: str) -> int:
    """
    Heuristic syllable counter for Spanish.
    Based on vowels and common diphthongs.
    """
    word = word.lower()
    # Remove non-alphabetic characters
    word = re.sub(r"[^a-záéíóúüñ]", "", word)
    if not word:
        return 0

    # Basic vowel groups that usually form a single syllable in Spanish (diphthongs/triphthongs)
    vowels = "aeiouáéíóúü"
    # Simple heuristic: count groups of vowels, but separate strong vowels (a, e, o)
    # This is a simplification but works for many common cases.
    count = 0
    i = 0
    n = len(word)
    while i < n:
        if word[i] in vowels:
            count += 1
            # Skip consecutive vowels that might form a diphthong
            while i + 1 < n and word[i + 1] in vowels:
                # Check for hiatus (two strong vowels or stressed weak vowel)
                strong = "aeoáéíóú"
                if word[i] in strong and word[i + 1] in strong:
                    # Hiatus usually splits
                    pass
                else:
                    # Diphthong stays together for this count
                    pass
                i += 1
        i += 1
    return count


def count_syllables_en(word: str) -> int:
    """
    Heuristic syllable counter for English.
    """
    word = word.lower()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0

    # Basic English heuristic
    vowels = "aeiouy"
    count = 0
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    if count == 0:
        count = 1
    return count


def get_syllables(text: str) -> int:
    """Aggregate syllable count for a line or block of text."""
    # Detect language roughly (default to Spanish if many accents found)
    has_accents = bool(re.search(r"[áéíóúüñ]", text, re.I))
    counter = count_syllables_es if has_accents else count_syllables_en

    words = text.split()
    return sum(counter(w) for w in words)


class HaikuGuard:
    """Validates the 5-7-5 structure (Ω₄)."""

    @staticmethod
    def validate(content: str) -> bool:
        """
        Check if content follows the 5-7-5 pattern.
        Expects lines separated by newlines or markers.
        """
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if len(lines) != 3:
            # Try splitting by punctuation if not newline separated
            lines = [line.strip() for line in re.split(r"[,;.]", content) if line.strip()]
            if len(lines) != 3:
                return False

        counts = [get_syllables(line) for line in lines]

        # Allowed tolerance for heuristic inaccuracy (+/- 1 per line)
        expected = [5, 7, 5]
        for actual, target in zip(counts, expected, strict=False):
            if abs(actual - target) > 1:
                logger.debug(
                    "Haiku Guard: Mismatch in line (Actual: %d, Target: %d)", actual, target
                )
                return False

        return True

    @staticmethod
    def enforce(content: str, metadata: Mapping[str, Any]) -> None:
        """Enforces Ω₄ for sacred artifacts."""
        is_sacred = metadata.get("fact_type") == "axiom" or "sacred" in metadata.get("tags", [])

        if is_sacred and not HaikuGuard.validate(content):
            raise GuardViolation(
                "Axiom rejected (Ω₄): Sacred truths must be aesthetically compressed into a Haiku (5-7-5)."
            )
