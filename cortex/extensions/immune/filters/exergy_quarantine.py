"""Exergy Quarantine Filter — blocks low-information-density signals.

F6: If a proposed signal/fact has Shannon exergy (information density) below a threshold,
it carries no new useful work and must be quarantined before the membrane
wastes guards and DB cycles on it.

Exergy is computed on the signal content (string or dict) using character
frequency distribution. This is a fast O(n) gate — no async I/O required.

Score mapping:
  exergy >= HIGH_EXERGY_THRESHOLD (≥3.5 bits) → PASS  (score 100)
  exergy >= MID_EXERGY_THRESHOLD  (≥2.5 bits) → HOLD  (score ~50)
  exergy < MID_EXERGY_THRESHOLD               → BLOCK (score 0)

Typical human text: 4.5–5.5 bits per character.
Noise/garbage strings: <2.0 bits.
Repeated words / trivial content: 2.0–3.0 bits.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any

from cortex.extensions.immune.filters.base import FilterResult, ImmuneFilter, Verdict

__all__ = ["ExergyQuarantineFilter"]

HIGH_EXERGY_THRESHOLD = 3.5  # bits — PASS, signal carries real information
MID_EXERGY_THRESHOLD = 2.5  # bits — HOLD, marginal signal

_SCORE_PASS = 100.0
_SCORE_HOLD = 50.0
_SCORE_BLOCK = 0.0


def _shannon_exergy(text: str) -> float:
    """Compute Shannon exergy (bits per character) of a string."""
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


class ExergyQuarantineFilter(ImmuneFilter):
    """F6 — Blocks zero-exergy / low-information signals before they enter the membrane.

    Prevents trivial, repetitive, or vacuous facts from consuming guard
    cycles, embedding compute, and ledger space.
    """

    @property
    def filter_id(self) -> str:
        return "F6"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Compute exergy of the signal and issue a verdict."""
        text = _extract_text(signal)
        exergy = _shannon_exergy(text)

        high_t = float(context.get("exergy_high_threshold", HIGH_EXERGY_THRESHOLD))
        mid_t = float(context.get("exergy_mid_threshold", MID_EXERGY_THRESHOLD))

        if exergy >= high_t:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.PASS,
                score=_SCORE_PASS,
                justification=(
                    f"Exergy {exergy:.3f} bits ≥ {high_t} — signal carries real information."
                ),
                metadata={"exergy_bits": round(exergy, 4), "text_len": len(text)},
            )
        if exergy >= mid_t:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.HOLD,
                score=_SCORE_HOLD,
                justification=(
                    f"Exergy {exergy:.3f} bits is marginal ({mid_t}–{high_t}). "
                    "Review signal before committing."
                ),
                metadata={"exergy_bits": round(exergy, 4), "text_len": len(text)},
            )

        # Below mid threshold — quarantine
        return FilterResult(
            filter_id=self.filter_id,
            verdict=Verdict.BLOCK,
            score=_SCORE_BLOCK,
            justification=(
                f"Exergy quarantine triggered: {exergy:.3f} bits < {mid_t}. "
                "Signal carries insufficient new information — blocked."
            ),
            metadata={"exergy_bits": round(exergy, 4), "text_len": len(text)},
        )
