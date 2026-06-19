"""
Batch scanning utilities for contradiction guard.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .models import ConflictCandidate
from .scoring import (
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _is_noise,
    _jaccard,
    _tokenize,
)


def _process_token_bucket(
    indices: list[int],
    group: list[dict],
    seen_pairs: set[tuple[int, int]],
    pairs: list[tuple[float, ConflictCandidate, ConflictCandidate]],
    min_score: float,
) -> None:
    """Compare all pairs within a token bucket."""
    if len(indices) < 2 or len(indices) > 50:
        return

    for i_pos in range(len(indices)):
        for j_pos in range(i_pos + 1, len(indices)):
            i, j = indices[i_pos], indices[j_pos]
            pair_key = (
                min(group[i]["id"], group[j]["id"]),
                max(group[i]["id"], group[j]["id"]),
            )
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            pair = _compare_decisions(group[i], group[j], min_score)
            if pair:
                pairs.append(pair)


def _compare_decisions(
    a: dict,
    b: dict,
    min_score: float,
) -> tuple[float, ConflictCandidate, ConflictCandidate] | None:
    """Score and classify a potential conflict between two decisions."""
    score = _jaccard(a["tokens"], b["tokens"])
    if score < min_score:
        return None

    # Batch-mode multipliers
    ctype = "keyword_overlap"
    if _detect_negation(a["content"]) or _detect_negation(b["content"]):
        ctype = "negation"
        score *= 1.3
    if _detect_supersession(a["content"]) or _detect_supersession(b["content"]):
        ctype = "version_supersede"
        score *= 1.2

    ca = ConflictCandidate(
        a["id"],
        a["project"],
        a["content"][:200],
        a["date"],
        min(score, 1.0),
        ctype,
    )
    cb = ConflictCandidate(
        b["id"],
        b["project"],
        b["content"][:200],
        b["date"],
        min(score, 1.0),
        ctype,
    )
    return (score, ca, cb)


def _prepare_decisions(
    rows: list,
    decrypt_fn: Callable | None,
) -> list[dict]:
    """Decrypt and tokenize raw database rows."""
    decisions = []
    for row in rows:
        content = _decrypt_content(row["content"], decrypt_fn)
        if not content or _is_noise(content):
            continue
        tokens = _tokenize(content)
        if len(tokens) < 3:
            continue
        decisions.append(
            {
                "id": row["id"],
                "project": row["project"],
                "content": content,
                "date": row["created_at"][:10],
                "tokens": tokens,
            }
        )
    return decisions


def _build_token_index(group: list[dict]) -> dict[str, list[int]]:
    """Build inverted index: token -> list of decision indices in the group."""
    token_index: dict[str, list[int]] = defaultdict(list)
    for idx, d in enumerate(group):
        top_tokens = sorted(d["tokens"], key=len, reverse=True)[:8]
        for token in top_tokens:
            token_index[token].append(idx)
    return token_index
