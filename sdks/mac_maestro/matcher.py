"""Mac-Maestro-Ω — Semantic Element Matcher.

Scoring pipeline: exact → casefold → substring → Levenshtein.
"""

from __future__ import annotations

import logging

from .models import AXNodeSnapshot, ElementMatch

logger = logging.getLogger("mac_maestro.matcher")

SCORE_THRESHOLD: float = 0.3
LEVENSHTEIN_SIMILARITY_THRESHOLD: float = 0.6

_W_ROLE_EXACT: float = 0.30
_W_TITLE_EXACT: float = 0.40
_W_TITLE_SUBSTRING: float = 0.20
_W_TITLE_CASEFOLD: float = 0.15
_W_TITLE_LEVENSHTEIN: float = 0.10
_W_DESCRIPTION: float = 0.15
_W_IDENTIFIER: float = 0.15
_W_ENABLED: float = 0.05


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance (pure Python, O(min(m,n)) space)."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(prev_row[j + 1] + 1, curr_row[j] + 1, prev_row[j] + cost))
        prev_row = curr_row
    return prev_row[-1]


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Normalized Levenshtein similarity in [0.0, 1.0]."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - _levenshtein_distance(s1, s2) / max_len


def _score_field(
    node_val: str | None,
    query_val: str | None,
    w_exact: float,
    w_sub: float,
    w_case: float,
    fuzzy: bool,
    w_levenshtein: float = _W_TITLE_LEVENSHTEIN,
) -> tuple[float, str | None]:
    """Score a single field match.

    Pipeline: exact → casefold → substring → Levenshtein.
    """
    if query_val is None or node_val is None:
        return 0.0, None
    if node_val == query_val:
        return w_exact, f"exact:{query_val}"
    if not fuzzy:
        return 0.0, None
    if node_val.casefold() == query_val.casefold():
        return w_case, f"casefold:{query_val}"
    if query_val.casefold() in node_val.casefold():
        return w_sub, f"substring:{query_val}"
    # Levenshtein fallback for typos
    sim = _levenshtein_similarity(node_val.casefold(), query_val.casefold())
    if sim >= LEVENSHTEIN_SIMILARITY_THRESHOLD:
        return w_levenshtein * sim, f"levenshtein:{query_val}(sim={sim:.2f})"
    return 0.0, None


def _score_node(
    node: AXNodeSnapshot,
    role: str | None,
    title: str | None,
    description: str | None,
    identifier: str | None,
    value: str | None,
    fuzzy: bool,
) -> tuple[float, list[str]]:
    """Calculate match score for a single AX node."""
    score = 0.0
    reasons: list[str] = []

    if role is not None and node.role == role:
        score += _W_ROLE_EXACT
        reasons.append(f"role={role}")

    delta, reason = _score_field(
        node.title,
        title,
        _W_TITLE_EXACT,
        _W_TITLE_SUBSTRING,
        _W_TITLE_CASEFOLD,
        fuzzy,
    )
    score += delta
    if reason:
        reasons.append(f"title:{reason}")

    delta, reason = _score_field(
        node.description,
        description,
        _W_DESCRIPTION,
        _W_DESCRIPTION * 0.6,
        _W_DESCRIPTION * 0.5,
        fuzzy,
    )
    score += delta
    if reason:
        reasons.append(f"desc:{reason}")

    if identifier is not None and node.identifier == identifier:
        score += _W_IDENTIFIER
        reasons.append(f"id={identifier}")

    delta, reason = _score_field(
        node.value,
        value,
        0.10,
        0.05,
        0.05,
        fuzzy,
    )
    score += delta
    if reason:
        reasons.append(f"value:{reason}")

    if node.enabled is True:
        score += _W_ENABLED
        reasons.append("enabled")

    return score, reasons


def _walk_tree(
    node: AXNodeSnapshot,
    role: str | None,
    title: str | None,
    description: str | None,
    identifier: str | None,
    value: str | None,
    fuzzy: bool,
    results: list[tuple[float, list[str], AXNodeSnapshot]],
) -> None:
    """Recursively walk AX tree and score each node."""
    score, reasons = _score_node(
        node,
        role,
        title,
        description,
        identifier,
        value,
        fuzzy,
    )
    if score >= SCORE_THRESHOLD:
        results.append((score, reasons, node))
    for child in node.children:
        _walk_tree(
            child,
            role,
            title,
            description,
            identifier,
            value,
            fuzzy,
            results,
        )


def find_elements(
    snapshot: AXNodeSnapshot,
    role: str | None = None,
    title: str | None = None,
    description: str | None = None,
    identifier: str | None = None,
    value: str | None = None,
    fuzzy: bool = True,
) -> list[ElementMatch]:
    """Search an AX tree for elements matching a semantic query.

    Returns list of ElementMatch sorted by score descending.
    """
    if all(v is None for v in (role, title, description, identifier, value)):
        return []

    raw: list[tuple[float, list[str], AXNodeSnapshot]] = []
    _walk_tree(
        snapshot,
        role,
        title,
        description,
        identifier,
        value,
        fuzzy,
        raw,
    )
    raw.sort(key=lambda x: x[0], reverse=True)

    return [
        ElementMatch(
            ref=node._ref,
            role=node.role,
            subrole=node.subrole,
            title=node.title,
            value=node.value,
            identifier=node.identifier,
            description=node.description,
            position=node.position,
            size=node.size,
            score=score,
            reasons=reasons,
        )
        for score, reasons, node in raw
    ]


def find_best(
    snapshot: AXNodeSnapshot,
    role: str | None = None,
    title: str | None = None,
    description: str | None = None,
    identifier: str | None = None,
    value: str | None = None,
    fuzzy: bool = True,
) -> ElementMatch | None:
    """Find the single best-matching element, or None."""
    results = find_elements(
        snapshot,
        role,
        title,
        description,
        identifier,
        value,
        fuzzy,
    )
    return results[0] if results else None
