from __future__ import annotations

from dataclasses import dataclass

from .errors import ElementAmbiguousError, ElementNotFoundError
from .models import AXNodeSnapshot, ElementMatch, ElementSelector, walk_nodes


@dataclass(slots=True, frozen=True)
class MatchWeights:
    role: float = 0.30
    subrole: float = 0.10
    title: float = 0.25
    description: float = 0.10
    value: float = 0.10
    contains_text: float = 0.15


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _score_text(expected: str | None, actual: str | None, weight: float, label: str) -> tuple[float, str | None]:
    if expected is None:
        return 0.0, None
    if _norm(expected) == _norm(actual):
        return weight, f"{label}:exact"
    return 0.0, None


def _score_contains(needle: str | None, *haystack: str | None, weight: float) -> tuple[float, str | None]:
    if needle is None:
        return 0.0, None
    n = _norm(needle)
    joined = " | ".join(_norm(x) for x in haystack)
    if n and n in joined:
        return weight, "contains_text:match"
    return 0.0, None


def score_node(node: AXNodeSnapshot, selector: ElementSelector, weights: MatchWeights | None = None) -> ElementMatch | None:
    weights = weights or MatchWeights()

    if selector.enabled is not None and node.enabled != selector.enabled:
        return None
    if selector.visible is not None and node.visible != selector.visible:
        return None

    reasons: list[str] = []
    score = 0.0

    s, r = _score_text(selector.role, node.role, weights.role, "role")
    score += s
    if r:
        reasons.append(r)

    s, r = _score_text(selector.subrole, node.subrole, weights.subrole, "subrole")
    score += s
    if r:
        reasons.append(r)

    s, r = _score_text(selector.title, node.title, weights.title, "title")
    score += s
    if r:
        reasons.append(r)

    s, r = _score_text(selector.description, node.description, weights.description, "description")
    score += s
    if r:
        reasons.append(r)

    s, r = _score_text(selector.value, node.value, weights.value, "value")
    score += s
    if r:
        reasons.append(r)

    s, r = _score_contains(
        selector.contains_text,
        node.title,
        node.description,
        node.value,
        weight=weights.contains_text,
    )
    score += s
    if r:
        reasons.append(r)

    if score <= 0:
        return None

    return ElementMatch(
        element_id=node.element_id,
        confidence=round(min(score, 1.0), 4),
        reasons=reasons,
        node=node,
    )


def find_best_match(root: AXNodeSnapshot, selector: ElementSelector) -> ElementMatch:
    candidates = [
        match
        for node in walk_nodes(root)
        if (match := score_node(node, selector)) is not None
    ]
    if not candidates:
        raise ElementNotFoundError(f"No element matched selector: {selector.model_dump()}")

    candidates.sort(key=lambda m: m.confidence, reverse=True)
    best = candidates[0]

    if len(candidates) > 1:
        second = candidates[1]
        if abs(best.confidence - second.confidence) < 0.05:
            raise ElementAmbiguousError(
                f"Ambiguous selector. top={best.confidence}, second={second.confidence}"
            )

    return best
