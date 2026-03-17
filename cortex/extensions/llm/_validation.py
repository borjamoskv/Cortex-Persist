# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router — DNSSEC Intent Validation.

Validates that a provider's response matches the requested intent.
Zero-cost heuristic validation (no LLM call required).

Extraído de router.py (Ω₂ Landauer split).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from cortex.extensions.llm._models import IntentProfile

__all__ = ["DriftSignal", "IntentValidator"]


# ─── DNSSEC (Intent Validation) ────────────────────────────────────────


@dataclass(frozen=True)
class DriftSignal:
    """DNSSEC validation result for a single response.

    Captures whether the response matched the requested intent,
    with confidence scoring and drift evidence.
    """

    provider: str
    """Provider that generated the response."""

    requested_intent: IntentProfile
    """What the prompt asked for."""

    detected_intent: IntentProfile
    """What the response actually looks like."""

    confidence: float
    """Detection confidence [0.0, 1.0]."""

    is_drift: bool
    """True if detected != requested and confidence > threshold."""

    evidence: str
    """Human-readable explanation of why drift was/wasn't detected."""

    timestamp: float = field(default_factory=time.monotonic)


class IntentValidator:
    """DNSSEC for LLM routing — post-response intent verification.

    Validates that a provider's response actually matches the requested
    intent. Uses heuristic signal detection (no LLM call required —
    zero-cost validation).

    DNS analogy:
        DNSSEC validates that the DNS response came from the authoritative
        server and wasn't tampered with. IntentValidator validates that the
        LLM response matches the semantic domain of the request.

    Drift detection signals:
        CODE: code fences, function defs, imports, syntax patterns
        REASONING: numbered steps, logical connectors, QED markers
        CREATIVE: narrative structure, dialogue, metaphors
        GENERAL: no strong signal (always passes)

    Axiom: Ω₃ (Byzantine Default) — verify, then trust. Never reversed.
    """

    # Minimum response length to attempt validation
    _MIN_VALIDATION_LENGTH: int = 50

    # Confidence threshold for flagging drift
    _DRIFT_CONFIDENCE_THRESHOLD: float = 0.6

    # ── Signal patterns (compiled once) ─────────────────────────────

    _CODE_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r"```\w*\n"),  # code fences
        re.compile(r"\bdef \w+\("),  # function defs
        re.compile(r"\bclass \w+[:(]"),  # class defs
        re.compile(r"\bimport \w+"),  # imports
        re.compile(r"\breturn \w+"),  # return statements
        re.compile(r"[{;}]\s*$", re.M),  # braces/semicolons
        re.compile(r"\b(if|for|while)\s*\("),  # control flow
        re.compile(r"=>|->|::\s*\w+"),  # arrows/type annotations
    )

    _REASONING_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r"^\d+\.\s", re.M),  # numbered steps
        re.compile(r"\b(therefore|hence|thus|consequently|because|since)\b", re.I),
        re.compile(r"\b(first|second|third|finally|in conclusion)\b", re.I),
        re.compile(r"\b(analysis|hypothesis|evidence|conclusion|reasoning)\b", re.I),
        re.compile(r"\b(if .+ then)\b", re.I),  # conditional logic
        re.compile(r"[\+\-\*/=<>].*[\+\-\*/=<>]"),  # mathematical ops
    )

    _CREATIVE_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r'["\u201c\u201d].{10,}["\u201c\u201d]'),  # dialogue
        re.compile(r"\b(once upon|story|narrative|imagine|dream)\b", re.I),
        re.compile(r"\b(metaphor|simile|poetry|verse|stanza)\b", re.I),
        re.compile(r"\b(chapter|scene|act|protagonist|character)\b", re.I),
        re.compile(r"[!]{2,}"),  # emphatic punctuation
        re.compile(r"\b(felt|whispered|sighed|gazed|wandered)\b", re.I),
    )

    def validate(
        self,
        response: str,
        requested_intent: IntentProfile,
        provider_name: str,
    ) -> DriftSignal:
        """Validate that a response matches the requested intent.

        Returns a DriftSignal with detection results. GENERAL intent
        always passes (no signal required).
        """
        # GENERAL never drifts — it accepts everything
        if requested_intent is IntentProfile.GENERAL:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=IntentProfile.GENERAL,
                confidence=1.0,
                is_drift=False,
                evidence="GENERAL intent — no validation required",
            )

        # Too short to validate meaningfully
        if len(response) < self._MIN_VALIDATION_LENGTH:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=requested_intent,  # benefit of the doubt
                confidence=0.0,
                is_drift=False,
                evidence=f"Response too short ({len(response)} chars) for validation",
            )

        # Score each domain
        scores = {
            IntentProfile.CODE: self._score(response, self._CODE_SIGNALS),
            IntentProfile.REASONING: self._score(response, self._REASONING_SIGNALS),
            IntentProfile.CREATIVE: self._score(response, self._CREATIVE_SIGNALS),
        }

        # Detected intent = highest scoring domain
        detected = max(scores, key=lambda k: scores[k])
        detected_score = scores[detected]
        requested_score = scores.get(requested_intent, 0.0)

        # Confidence: how much stronger is the detected signal vs requested
        if detected_score == 0.0:
            # No signals at all — can't determine, benefit of the doubt
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=requested_intent,
                confidence=0.0,
                is_drift=False,
                evidence="No domain signals detected",
            )

        if detected == requested_intent:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=detected,
                confidence=detected_score,
                is_drift=False,
                evidence=f"Matched: {detected.value} score={detected_score:.2f}",
            )

        # Drift detected — response doesn't match requested intent
        drift_confidence = detected_score - requested_score
        is_drift = drift_confidence >= self._DRIFT_CONFIDENCE_THRESHOLD

        return DriftSignal(
            provider=provider_name,
            requested_intent=requested_intent,
            detected_intent=detected,
            confidence=drift_confidence,
            is_drift=is_drift,
            evidence=(
                f"Drift: requested={requested_intent.value}(score={requested_score:.2f}) "
                f"but detected={detected.value}(score={detected_score:.2f}) "
                f"delta={drift_confidence:.2f}"
            ),
        )

    @staticmethod
    def _score(text: str, patterns: tuple[re.Pattern[str], ...]) -> float:
        """Score how strongly text matches a set of signal patterns.

        Returns [0.0, 1.0] where 1.0 = all patterns matched.
        """
        if not patterns:
            return 0.0
        matches = sum(1 for p in patterns if p.search(text))
        return matches / len(patterns)
