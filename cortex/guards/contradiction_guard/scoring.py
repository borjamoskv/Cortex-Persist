"""
Scoring and classification logic for contradiction guard.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import aiosqlite

from cortex.utils.void_vec import cosine_similarity

from .models import ConflictCandidate

EMBEDDING_BOOST_WEIGHT = 0.3  # Max boost from embedding similarity
_embedding_cosine_similarity = cosine_similarity

_NOISE_PREFIXES = ("MAILTV-1: ARCHIVE",)
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
    """Extract meaningful tokens from content."""
    tokens = set(re.findall(r"[a-záéíóúñ]{3,}", text.lower()))
    return tokens - _STOP_WORDS


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity coefficient."""
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _detect_negation(content: str) -> bool:
    """Check if content contains negation/prohibition language."""
    content_lower = content.lower()
    return any(marker in content_lower for marker in _NEGATION_MARKERS)


def _detect_supersession(content: str) -> bool:
    """Check if content explicitly supersedes prior versions."""
    return bool(_SUPERSESSION_MARKERS.search(content))


def _extract_versions(content: str) -> list[str]:
    """Extract version numbers (e.g., v1.2) from content."""
    return _VERSION_PATTERN.findall(content)


def _is_noise(content: str) -> bool:
    """Filter out noise/archive records."""
    return content.startswith(_NOISE_PREFIXES)


def _decrypt_content(content: str, decrypt_fn: Callable | None) -> str | None:
    """Decrypt content if a decrypter is provided."""
    if not decrypt_fn or not content.startswith("v6_aesgcm:"):
        return content
    try:
        return decrypt_fn(content)
    except (ValueError, TypeError, OSError):
        return None


def _classify_conflict(
    new_content: str,
    existing_content: str,
    new_tokens: set[str],
    existing_tokens: set[str],
    base_score: float,
) -> tuple[str, float]:
    """Classify conflict type and apply score multipliers."""
    conflict_type = "keyword_overlap"

    if _detect_negation(new_content) or _detect_negation(existing_content):
        conflict_type = "negation"
        base_score *= 1.5

    if _detect_supersession(new_content) or _detect_supersession(existing_content):
        conflict_type = "version_supersede"
        base_score *= 1.2

    new_versions = _extract_versions(new_content)
    old_versions = _extract_versions(existing_content)
    if new_versions and old_versions and len(new_tokens & existing_tokens) > 5:
        conflict_type = "version_supersede"
        base_score *= 1.4

    return conflict_type, base_score


def _score_candidate(
    row: aiosqlite.Row,
    new_tokens: set[str],
    new_content: str,
    new_project: str,
    decrypt_fn: Callable | None,
    min_score: float,
    new_embedding: list[float] | None = None,
    existing_embedding: list[float] | None = None,
) -> ConflictCandidate | None:
    """Score a single row against new content. Returns None if below threshold."""
    content = _decrypt_content(row["content"], decrypt_fn)
    if not content or _is_noise(content):
        return None

    existing_tokens = _tokenize(content)
    score = _jaccard(new_tokens, existing_tokens)

    # Project boost: same project = 1.3x
    if row["project"] == new_project:
        score *= 1.3

    # Layer 4: Embedding cosine similarity boost (Ω₁₃ upgrade)
    cosine_sim = cosine_similarity(new_embedding, existing_embedding)
    if cosine_sim > 0.5:
        score += EMBEDDING_BOOST_WEIGHT * cosine_sim

    if score < min_score:
        return None

    conflict_type, score = _classify_conflict(
        new_content,
        content,
        new_tokens,
        existing_tokens,
        score,
    )

    # If embedding similarity is very high but Jaccard is low, flag as semantic conflict
    if cosine_sim > 0.8 and _jaccard(new_tokens, existing_tokens) < 0.2:
        conflict_type = "semantic_similarity"

    return ConflictCandidate(
        fact_id=row["id"],
        project=row["project"],
        content=content[:300],
        date=row["created_at"][:10],
        overlap_score=min(score, 1.0),
        conflict_type=conflict_type,
    )
