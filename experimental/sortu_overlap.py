# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "is",
    "not",
    "the",
    "this",
    "that",
    "with",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) >= 3 and token not in _STOPWORDS]


def _cosine_similarity(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_counts = Counter(left)
    right_counts = Counter(right)
    vocab = set(left_counts) | set(right_counts)
    dot = sum(left_counts[token] * right_counts[token] for token in vocab)
    left_norm = math.sqrt(sum(count * count for count in left_counts.values()))
    right_norm = math.sqrt(sum(count * count for count in right_counts.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


@dataclass(frozen=True)
class OverlapDecision:
    decision: str
    overlap_score: float
    causal_gap_score: float


class OverlapDetector:
    def __init__(self, skills_dir: str | Path) -> None:
        self.skills_dir = Path(skills_dir)

    def scan_existing_skills(self) -> list[Path]:
        if not self.skills_dir.exists():
            return []
        return sorted(
            [
                path
                for path in self.skills_dir.iterdir()
                if path.is_dir() and (path / "SKILL.md").exists()
            ]
        )

    def _skill_texts(self) -> list[str]:
        texts: list[str] = []
        for skill_dir in self.scan_existing_skills():
            texts.append((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        return texts

    def compute_causal_gap(self, intent: str) -> float:
        intent_tokens = _tokenize(intent)
        if not intent_tokens:
            return 0.0
        existing_tokens = {
            token for text in self._skill_texts() for token in _tokenize(text)
        }
        if not existing_tokens:
            return 1.0
        novel = [token for token in intent_tokens if token not in existing_tokens]
        return len(novel) / len(intent_tokens)

    def decide(
        self,
        intent: str,
        *,
        overlap_threshold: float = 0.9,
        causal_gap_threshold: float = 0.15,
    ) -> OverlapDecision:
        intent_tokens = _tokenize(intent)
        overlap_score = 0.0
        for text in self._skill_texts():
            overlap_score = max(overlap_score, _cosine_similarity(intent_tokens, _tokenize(text)))
        causal_gap_score = self.compute_causal_gap(intent)
        decision = (
            "ABORT_REDUNDANT"
            if overlap_score >= overlap_threshold and causal_gap_score < causal_gap_threshold
            else "PROCEED"
        )
        return OverlapDecision(
            decision=decision,
            overlap_score=round(overlap_score, 6),
            causal_gap_score=round(causal_gap_score, 6),
        )
