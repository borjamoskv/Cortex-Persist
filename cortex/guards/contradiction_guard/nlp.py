"""
Natural Language Processing and text utilities for the Contradiction Guard.

Provides text tokenization, filtering, decryption handling, and marker
detection (e.g., negations or supersession language) to identify semantic conflicts.
"""

from __future__ import annotations

import re
from collections.abc import Callable

_NOISE_PREFIXES = frozenset(
    {
        "MAILTV archive",
        "LOG:",
        "DEBUG:",
        "TRACE:",
        "METRIC:",
    }
)

_STOP_WORDS = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "y",
        "o",
        "pero",
        "si",
        "no",
        "en",
        "por",
        "para",
        "con",
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

_NEGATION_MARKERS = frozenset(
    {
        "no usar",
        "never use",
        "prohibido",
        "eliminado",
        "forbidden",
        "deprecated",
        "removed",
        "replaced",
        "reemplazado",
        "obsolete",
        "no utilizar",
        "don't use",
        "do not use",
        "eliminamos",
        "matado",
        "killed",
        "purged",
        "deleted",
    }
)

_SUPERSESSION_MARKERS = re.compile(
    r"supersed|replac|obsolet|invalidat|deprecat|eliminad|reemplaz|upgrade|migrat|refactor",
    re.IGNORECASE,
)

_VERSION_PATTERN = re.compile(r"\b[vV](\d+(?:\.\d+)*)\b")


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from content.

    Args:
        text: The raw text string.

    Returns:
        A set of tokens excluding predefined stop words.
    """
    tokens = set(re.findall(r"[a-záéíóúñ]{3,}", text.lower()))
    return tokens - _STOP_WORDS


def _jaccard(a: set[str], b: set[str]) -> float:
    """Calculate the Jaccard similarity coefficient between two token sets.

    Args:
        a: First set of tokens.
        b: Second set of tokens.

    Returns:
        The Jaccard similarity coefficient (0.0 to 1.0).
    """
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _detect_negation(content: str) -> bool:
    """Check if content contains negation or prohibition language.

    Args:
        content: The text content to analyze.

    Returns:
        True if any negation markers are found, False otherwise.
    """
    content_lower = content.lower()
    return any(marker in content_lower for marker in _NEGATION_MARKERS)


def _detect_supersession(content: str) -> bool:
    """Check if content contains supersession language.

    Args:
        content: The text content to analyze.

    Returns:
        True if supersession markers are matched, False otherwise.
    """
    return bool(_SUPERSESSION_MARKERS.search(content))


def _extract_versions(content: str) -> list[str]:
    """Extract version numbers from content.

    Args:
        content: The text content.

    Returns:
        A list of version strings found in the content.
    """
    return _VERSION_PATTERN.findall(content)


def _is_noise(content: str) -> bool:
    """Filter out noise decisions like MAILTV archives or simple logs.

    Args:
        content: The text content.

    Returns:
        True if the content matches known noise prefixes, False otherwise.
    """
    return any(content.startswith(prefix) for prefix in _NOISE_PREFIXES)


def _decrypt_content(content: str, decrypt_fn: Callable[[str], str] | None) -> str | None:
    """Decrypt content if needed, returning None on failure.

    Args:
        content: The potentially encrypted text content.
        decrypt_fn: An optional decryption callable.

    Returns:
        The decrypted content, or the original content if no decryption is needed.
        Returns None if decryption fails.
    """
    if not decrypt_fn or not content.startswith("v6_aesgcm:"):
        return content
    try:
        return decrypt_fn(content)
    except (ValueError, TypeError, OSError):
        return None
