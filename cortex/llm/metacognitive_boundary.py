# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v8.0 — Metacognitive Boundary Layer.

Sprint 1 of the 130/100 plan: closes the LLM↔Memory gap.

Previously, `ImmuneBoundary` only validated JSON structure.
The LLM could ignore retrieved memories, hallucinate confidently
despite low FOK scores, and produce responses inconsistent with
the metamemory state.

This module solves the "blind LLM" problem in three steps:

  1. PREAMBLE: Injects FOK/JOL/Verdict signals into the system prompt
               so the LLM knows what it knows BEFORE generating.

  2. PLAN: Forces the LLM to declare a "retrieval plan" —
           which memories it will use and why — BEFORE answering.

  3. VERIFY: Post-generation consistency check to detect when the
             response contradicts or ignores the memory evidence.

Axiom derivation:
  Ω₃ (Byzantine Default) + Ω₄ (Aesthetic Integrity):
  An LLM that ignores its own memory is a Byzantine node.
  The boundary is the verification protocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from cortex.memory.metamemory import MemoryCard, MetaJudgment, Verdict

logger = logging.getLogger("cortex.llm.metacognitive_boundary")

# ─── Constants ────────────────────────────────────────────────────────

# Confidence threshold below which we hard-block an overconfident response
_ABSTAIN_CONFIDENCE_CAP: float = 0.2

# Max characters of epistemic preamble injected into the system prompt
_MAX_PREAMBLE_CHARS: int = 1200

# Minimum verdict confidence to allow a RESPOND verdict through
_RESPOND_CONFIDENCE_FLOOR: float = 0.5


# ─── Calibration Signal ───────────────────────────────────────────────


class EpistemicSignal(str, Enum):
    """Human-readable epistemic state passed to the LLM."""

    CONFIDENT = "confident"  # FOK high, Verdict=RESPOND
    PARTIAL = "partial"  # FOK moderate, Verdict=SEARCH_MORE
    UNCERTAIN = "uncertain"  # FOK low, Verdict=ABSTAIN or near
    TOT = "tip_of_tongue"  # FOK high but retrieval blocked


# ─── Metacognitive Context ────────────────────────────────────────────


@dataclass(frozen=True)
class MetacognitiveContext:
    """Epistemic snapshot passed from memory layer to LLM layer.

    All the signals the LLM needs to calibrate its response:
      - verdict: The metacognitive judge's decision
      - judgment: Full FOK/JOL/confidence breakdown
      - memory_cards: The actual memory evidence
      - signal: Plain-English epistemic state label
    """

    verdict: Verdict
    judgment: MetaJudgment
    memory_cards: list[MemoryCard]
    signal: EpistemicSignal
    knowledge_gaps: list[str]
    domain_calibration: float = -1.0  # Ω₁: Segmented Brier Score

    @property
    def should_hard_block(self) -> bool:
        """Hard-block a confident response when confidence is too low.

        Prevents the LLM from outputting high-confidence claims
        when the memory system has no reliable evidence.
        The LLM must use hedging language if confidence is below floor.
        """
        return (
            self.verdict == Verdict.ABSTAIN and self.judgment.confidence < _ABSTAIN_CONFIDENCE_CAP
        )

    @property
    def card_summaries(self) -> list[dict[str, Any]]:
        """Condensed memory card summaries for prompt injection."""
        return [
            {
                "id": c.memory_id,
                "confidence": round(c.retrieval_confidence, 3),
                "existence": round(c.existence_probability, 3),
                "status": c.consolidation_status,
                "needs_repair": c.repair_needed,
                "emotional_weight": round(c.emotional_weight, 2),
            }
            for c in self.memory_cards
        ]


# ─── Context Factory ─────────────────────────────────────────────────


def build_metacognitive_context(
    *,
    verdict: Verdict,
    judgment: MetaJudgment,
    memory_cards: list[MemoryCard] | None = None,
    knowledge_gaps: list[str] | None = None,
) -> MetacognitiveContext:
    """Compose a MetacognitiveContext from metamemory outputs.

    Derives the EpistemicSignal automatically:
      - TOT if tip_of_tongue is flagged
      - CONFIDENT if verdict=RESPOND and confidence high
      - PARTIAL if verdict=SEARCH_MORE
      - UNCERTAIN otherwise
    """
    cards = memory_cards or []
    gaps = knowledge_gaps or []

    if judgment.tip_of_tongue:
        signal = EpistemicSignal.TOT
    elif verdict == Verdict.RESPOND and judgment.confidence >= _RESPOND_CONFIDENCE_FLOOR:
        signal = EpistemicSignal.CONFIDENT
    elif verdict == Verdict.SEARCH_MORE:
        signal = EpistemicSignal.PARTIAL
    else:
        signal = EpistemicSignal.UNCERTAIN

    return MetacognitiveContext(
        verdict=verdict,
        judgment=judgment,
        memory_cards=cards,
        signal=signal,
        knowledge_gaps=gaps,
        domain_calibration=-1.0,  # Default, up to caller to fill
    )


# ─── Preamble Generator ──────────────────────────────────────────────


def build_epistemic_preamble(ctx: MetacognitiveContext) -> str:
    """Generate the metacognitive preamble injected into the system prompt.

    This gives the LLM its "epistemic situation" before it generates:
      - What the memory system found
      - How confident it is
      - What action it should take
      - What gaps exist (TOT patterns)

    The preamble is capped at _MAX_PREAMBLE_CHARS to avoid token waste (Ω₂).
    """
    verdict_str = ctx.verdict.value.upper()
    fok = round(ctx.judgment.fok_score, 3)
    jol = round(ctx.judgment.jol_score, 3)
    conf = round(ctx.judgment.confidence, 3)
    accessibility = round(ctx.judgment.accessibility, 3)
    signal = ctx.signal.value
    brier = ctx.domain_calibration

    lines: list[str] = [
        "--- [CORTEX EPISTEMIC STATE] ---",
        f"Signal: {signal.upper()}",
        f"Verdict: {verdict_str}",
        f"FOK (Feeling-of-Knowing): {fok:.3f}  | JOL (Encoding quality): {jol:.3f}",
        f"Confidence: {conf:.3f}  | Accessibility: {accessibility:.3f}",
    ]

    if brier >= 0:
        cal_status = "STABLE" if brier < 0.15 else "DRIFTING" if brier < 0.35 else "UNRELIABLE"
        lines.append(f"Domain Calibration: {brier:.4f} ({cal_status})")
        if brier > 0.35:
            lines.append(
                "⚠ WARNING: High calibration drift detected for this domain. "
                "Your previous answers here were overconfident. Be extremely conservative."
            )

    if ctx.judgment.tip_of_tongue:
        lines.append(
            "⚠ TIP-OF-TONGUE DETECTED: Knowledge likely exists but is currently inaccessible. "
            "Hedge your response. Do not confabulate."
        )

    if ctx.should_hard_block:
        lines.append(
            "🚫 EPISTEMIC HARD BLOCK: Confidence below minimum threshold. "
            "You MUST respond with 'I don't have reliable information about this.' "
            "Do NOT speculate or fabricate. Ω₃ — Byzantine Default active."
        )

    if ctx.knowledge_gaps:
        gap_list = ", ".join(f'"{g}"' for g in ctx.knowledge_gaps[:5])
        lines.append(f"Known knowledge gaps: {gap_list}")

    if ctx.memory_cards:
        lines.append(f"Memory evidence: {len(ctx.memory_cards)} engrams retrieved.")
        usable = [c for c in ctx.memory_cards if not c.repair_needed]
        broken = len(ctx.memory_cards) - len(usable)
        if broken:
            lines.append(f"  ⚠ {broken} engram(s) flagged for repair — do not rely on them.")
        if usable:
            best = max(usable, key=lambda c: c.retrieval_confidence)
            lines.append(
                f"  Best evidence: id={best.memory_id}, "
                f"conf={best.retrieval_confidence:.3f}, "
                f"status={best.consolidation_status}"
            )
    else:
        lines.append("Memory evidence: NONE — no engrams retrieved for this query.")

    # Verdict-specific instruction
    if ctx.verdict == Verdict.RESPOND:
        lines.append(
            "INSTRUCTION: Memory evidence is sufficient. Respond with calibrated confidence."
        )
    elif ctx.verdict == Verdict.SEARCH_MORE:
        lines.append(
            "INSTRUCTION: Memory evidence is partial. If you respond, explicitly state "
            "the limits of your knowledge. Consider asking for clarification."
        )
    else:
        lines.append(
            "INSTRUCTION: Memory evidence is insufficient. Respond with 'I don't know' "
            "or ask for more context. Do NOT confabulate."
        )

    lines.append("--- [END EPISTEMIC STATE] ---")

    preamble = "\n".join(lines)
    # Hard cap — Ω₂: entropic asymmetry
    return preamble[:_MAX_PREAMBLE_CHARS]


# ─── System Prompt Injector ──────────────────────────────────────────


def inject_epistemic_preamble(
    system_prompt: str,
    ctx: MetacognitiveContext,
) -> str:
    """Prepend the epistemic preamble to an existing system prompt.

    Placement: BEFORE the main prompt so the LLM sees its epistemic
    state before its role/instructions. This mirrors human metacognition:
    you assess your knowledge state before you decide what to say.
    """
    preamble = build_epistemic_preamble(ctx)
    if system_prompt:
        return f"{preamble}\n\n{system_prompt}"
    return preamble


# ─── Retrieval Plan Enforcer ─────────────────────────────────────────


RETRIEVAL_PLAN_SUFFIX = """

Before answering, declare your retrieval plan in this exact format:
<retrieval_plan>
Using: [list the memory IDs or "none" if no memories retrieved]
Reason: [why these memories are relevant]
Confidence: [your calibrated confidence 0.0-1.0]
</retrieval_plan>

Then provide your answer."""


def append_retrieval_plan_request(user_message: str) -> str:
    """Append retrieval plan declaration requirement to user message.

    Forces the LLM to make its memory usage explicit before answering.
    This prevents silent memory-ignoring — an LLM that declares it used
    no memories but then states facts confidently is detectable.
    """
    return f"{user_message}{RETRIEVAL_PLAN_SUFFIX}"


# ─── Consistency Verifier ────────────────────────────────────────────


def verify_retrieval_plan_declared(response: str) -> bool:
    """Check that the LLM declared a retrieval plan in its response.

    Returns True if <retrieval_plan>...</retrieval_plan> is present.
    A missing plan is a soft violation — logged, not raised.
    """
    has_open = "<retrieval_plan>" in response
    has_close = "</retrieval_plan>" in response
    declared = has_open and has_close

    if not declared:
        logger.warning(
            "MetacognitiveBoundary: LLM did not declare retrieval plan. "
            "Memory usage is opaque. Consider retry with stricter prompt."
        )

    return declared


def extract_declared_confidence(response: str) -> float | None:
    """Extract the declared confidence from the retrieval plan block.

    Returns float in [0.0, 1.0] or None if not found/parseable.
    """
    import re

    match = re.search(
        r"<retrieval_plan>.*?Confidence:\s*([0-9.]+).*?</retrieval_plan>",
        response,
        re.DOTALL,
    )
    if not match:
        return None

    try:
        val = float(match.group(1))
        return max(0.0, min(1.0, val))
    except ValueError:
        return None


def check_confidence_consistency(
    declared_confidence: float,
    metacognitive_confidence: float,
    tolerance: float = 0.25,
) -> bool:
    """Verify the LLM's declared confidence is consistent with metamemory.

    A large gap between what the memory system found (metacognitive_confidence)
    and what the LLM claims (declared_confidence) is a red flag for
    confabulation or memory-ignoring.

    Logs a warning if inconsistency exceeds tolerance.
    Returns True if consistent, False if suspicious.
    """
    delta = abs(declared_confidence - metacognitive_confidence)
    consistent = delta <= tolerance

    if not consistent:
        logger.warning(
            "MetacognitiveBoundary: Confidence inconsistency detected. "
            "LLM declared=%.3f, metamemory=%.3f, delta=%.3f (tolerance=%.2f). "
            "Possible confabulation.",
            declared_confidence,
            metacognitive_confidence,
            delta,
            tolerance,
        )

    return consistent


# ─── Public API ──────────────────────────────────────────────────────

__all__ = [
    "EpistemicSignal",
    "MetacognitiveContext",
    "append_retrieval_plan_request",
    "build_epistemic_preamble",
    "build_metacognitive_context",
    "check_confidence_consistency",
    "extract_declared_confidence",
    "inject_epistemic_preamble",
    "verify_retrieval_plan_declared",
]
