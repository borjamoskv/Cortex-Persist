"""Entropic Quarantine Filter — blocks low-information-density signals.

F6: If a proposed signal/fact has Shannon entropy below a threshold,
it carries no new information and must be quarantined before the membrane
wastes guards and DB cycles on it.

Entropy is computed on the signal content (string or dict) using character
frequency distribution. This is a fast O(n) gate — no async I/O required.

Score mapping:
  entropy >= HIGH_ENTROPY_THRESHOLD (≥3.5 bits) → PASS  (score 100)
  entropy >= MID_ENTROPY_THRESHOLD  (≥2.5 bits) → HOLD  (score ~50)
  entropy < MID_ENTROPY_THRESHOLD               → BLOCK (score 0)

Typical human text: 4.5–5.5 bits per character.
Noise/garbage strings: <2.0 bits.
Repeated words / trivial content: 2.0–3.0 bits.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any

from cortex.immune.filters.base import FilterResult, ImmuneFilter, Verdict

__all__ = ["EntropicQuarantineFilter"]

HIGH_ENTROPY_THRESHOLD = 3.5  # bits — PASS, signal carries real information
MID_ENTROPY_THRESHOLD = 2.5  # bits — HOLD, marginal signal

_SCORE_PASS = 100.0
_SCORE_HOLD = 50.0
_SCORE_BLOCK = 0.0


def _shannon_entropy(text: str) -> float:
    """Compute Shannon entropy (bits per character) of a string."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def _extract_text(signal: Any) -> str:
    """Best-effort extraction of a text representation from the signal."""
    if isinstance(signal, str):
        return signal
    if isinstance(signal, dict):
        # Prefer 'content' key if present, otherwise serialize the whole dict
        if "content" in signal:
            return str(signal["content"])
        try:
            return json.dumps(signal, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(signal)
    return str(signal)


class EntropicQuarantineFilter(ImmuneFilter):
    """F6 — Blocks zero-entropy / low-information signals before they enter the membrane.

    Prevents trivial, repetitive, or vacuous facts from consuming guard
    cycles, embedding compute, and ledger space.
    """

    @property
    def filter_id(self) -> str:
        return "F6"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Compute entropy of the signal and issue a verdict."""
        text = _extract_text(signal)
        entropy = _shannon_entropy(text)

        # Context can override threshold (e.g. for structured data)
        high_t = float(context.get("entropy_high_threshold", HIGH_ENTROPY_THRESHOLD))
        mid_t = float(context.get("entropy_mid_threshold", MID_ENTROPY_THRESHOLD))

        if entropy >= high_t:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.PASS,
                score=_SCORE_PASS,
                justification=(
                    f"Entropy {entropy:.3f} bits ≥ {high_t} — signal carries real information."
                ),
                metadata={"entropy_bits": round(entropy, 4), "text_len": len(text)},
            )
        if entropy >= mid_t:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.HOLD,
                score=_SCORE_HOLD,
                justification=(
                    f"Entropy {entropy:.3f} bits is marginal ({mid_t}–{high_t}). "
                    "Review signal before committing."
                ),
                metadata={"entropy_bits": round(entropy, 4), "text_len": len(text)},
            )

        # Below mid threshold — quarantine
        return FilterResult(
            filter_id=self.filter_id,
            verdict=Verdict.BLOCK,
            score=_SCORE_BLOCK,
            justification=(
                f"Entropic quarantine triggered: {entropy:.3f} bits < {mid_t}. "
                "Signal carries insufficient new information — blocked."
            ),
            metadata={"entropy_bits": round(entropy, 4), "text_len": len(text)},
        )
