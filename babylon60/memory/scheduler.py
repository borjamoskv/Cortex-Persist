# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX Memory Scheduler.

Implements the context scheduling tensor equation from Whitepaper §10:
Score(m) = (Rel·w_r + Conf·w_c + Rec·w_t) / (Cost_tokens + Risk_contam)
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Import from babylon60 extensions
try:
    from babylon60.extensions.hypervisor.belief_object import BeliefConfidence, BeliefObject
except ImportError:
    try:
        from babylon60.extensions.hypervisor.belief_object import BeliefConfidence, BeliefObject
    except ImportError:
        # Fallback dummy class if imports fail in isolated test environments
        class BeliefConfidence:  # type: ignore
            C1_HYPOTHESIS = "C1"
            C2_TENTATIVE = "C2"
            C3_PROBABLE = "C3"
            C4_CONFIRMED = "C4"
            C5_AXIOMATIC = "C5"

        class BeliefObject:  # type: ignore
            pass


logger = logging.getLogger(__name__)

# Map for confidence levels
CONFIDENCE_MAP = {
    "C1": 0.2,
    "C1_HYPOTHESIS": 0.2,
    "C2": 0.4,
    "C2_TENTATIVE": 0.4,
    "C3": 0.6,
    "C3_PROBABLE": 0.6,
    "C4": 0.8,
    "C4_CONFIRMED": 0.8,
    "C5": 1.0,
    "C5_AXIOMATIC": 1.0,
}


@dataclass
class SchedulerConfig:
    """Configuration weights and thresholds for the memory scheduler.

    Attributes:
        w_relevance: Weight for semantic relevance [0, 1].
        w_confidence: Weight for epistemic confidence [0, 1].
        w_recency: Weight for temporal freshness [0, 1].
        contamination_threshold: Risk limit above which beliefs are rejected.
        recency_decay_rate: Exponential decay rate lambda for recency decay.
    """

    w_relevance: float = 0.5
    w_confidence: float = 0.3
    w_recency: float = 0.2
    contamination_threshold: float = 0.7
    recency_decay_rate: float = 1e-6


class MemoryScheduler:
    """Memory scheduler implementing the tensor equation in Whitepaper §10.

    Evaluates context relevance, epistemic confidence, and temporal freshness
    against token cost and contamination risk to select optimal belief sets
    for inference context window.
    """

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        """Initialize the MemoryScheduler with optional config."""
        self.config = config or SchedulerConfig()

    def score(
        self,
        belief: Any,
        query: str | None = None,
        relevance: float | None = None,
        contamination_risk: float | None = None,
    ) -> float:
        """Calculate the scheduler score for a belief object.

        Equation:
            Score(m) = (Rel·w_r + Conf·w_c + Rec·w_t) / (Cost_tokens + Risk_contam)

        Args:
            belief: The BeliefObject instance.
            query: The search/context query string to match against.
            relevance: Explicit precomputed relevance score in [0.0, 1.0].
            contamination_risk: Explicit contamination risk in [0.0, 1.0].

        Returns:
            The calculated utility score (higher is better).
        """
        # 1. Relevance (Rel) with graceful fallback
        if relevance is None:
            relevance = self._calculate_fallback_relevance(belief, query)
        else:
            relevance = max(0.0, min(1.0, relevance))

        # 2. Confidence (Conf)
        confidence = self._extract_confidence_value(belief)

        # 3. Recency (Rec) with exponential decay
        recency = self._calculate_recency(belief)

        # 4. Token Cost (Cost_tokens)
        cost_tokens = self._extract_token_cost(belief)

        # 5. Contamination Risk (Risk_contam)
        if contamination_risk is None:
            contamination_risk = float(getattr(belief, "contamination_risk", 0.0))
        else:
            contamination_risk = max(0.0, min(1.0, contamination_risk))

        # Compute utility score
        numerator = (
            (relevance * self.config.w_relevance)
            + (confidence * self.config.w_confidence)
            + (recency * self.config.w_recency)
        )
        denominator = cost_tokens + contamination_risk

        # Guard against zero/negative denominator
        if denominator <= 0:
            denominator = 1e-6

        return numerator / denominator

    def admit(self, belief: Any, contamination_risk: float | None = None) -> bool:
        """Determine if a belief is admissible to be loaded into context.

        Rejects the belief if the contamination risk exceeds the threshold,
        or if the belief is explicitly quarantined.

        Args:
            belief: The BeliefObject instance.
            contamination_risk: Optional explicit contamination risk.

        Returns:
            True if the belief can be admitted, False otherwise.
        """
        # Fast path rejection for quarantined beliefs
        status = getattr(belief, "status", None)
        if status is not None:
            status_str = str(getattr(status, "value", status)).lower()
            if status_str == "quarantined":
                return False

        if hasattr(belief, "is_quarantined") and belief.is_quarantined():
            return False

        # Resolve contamination risk
        if contamination_risk is None:
            contamination_risk = float(getattr(belief, "contamination_risk", 0.0))

        return contamination_risk <= self.config.contamination_threshold

    def rank_beliefs(
        self,
        beliefs: list[Any],
        query: str | None = None,
        token_budget: int | None = None,
    ) -> list[Any]:
        """Rank a list of beliefs, filtering by admissibility and token budget.

        Args:
            beliefs: List of BeliefObject instances.
            query: Query string to compute relevance.
            token_budget: Max token budget allowed for the ranked list.

        Returns:
            Ordered list of admitted beliefs that fit within the token budget.
        """
        # Calculate scores and filter/sort
        scored: list[tuple[float, Any]] = []
        for belief in beliefs:
            if not self.admit(belief):
                continue
            score_val = self.score(belief, query=query)
            scored.append((score_val, belief))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Allocate budget
        ranked: list[Any] = []
        cumulative_tokens = 0.0

        for _, belief in scored:
            cost = self._extract_token_cost(belief)
            if token_budget is not None:
                if cumulative_tokens + cost > token_budget:
                    continue
            ranked.append(belief)
            cumulative_tokens += cost

        return ranked

    # ─── Helper Methods ──────────────────────────────────────────────────

    def _calculate_fallback_relevance(self, belief: Any, query: str | None) -> float:
        """Calculate fallback relevance score using proposition_key hash.

        Grades gracefully by computing a deterministic hash of the
        proposition_key combined with the query.
        """
        prop_key = getattr(belief, "proposition_key", None)
        if prop_key is None:
            prop_key = getattr(belief, "id", None)
        if prop_key is None:
            prop_key = getattr(belief, "content", "")

        prop_str = str(prop_key)
        query_str = query or ""

        # Deterministic fallback relevance mapping
        combined = f"{query_str}:{prop_str}"
        h = hashlib.sha256(combined.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big") / (2**64 - 1)

    def _extract_confidence_value(self, belief: Any) -> float:
        """Extract float confidence value in range [0.0, 1.0]."""
        conf_val = getattr(belief, "confidence", 0.5)
        if isinstance(conf_val, (int, float)):
            return float(conf_val)

        # Handle Enum or string representation
        val_str = str(getattr(conf_val, "value", conf_val))
        return CONFIDENCE_MAP.get(val_str, 0.5)

    def _calculate_recency(self, belief: Any) -> float:
        """Calculate temporal freshness using exponential decay.

        Uses: Rec = exp(-lambda * delta_t)
        Where delta_t = now - timestamp_last_verified
        """
        last_verified = self._resolve_last_verified_timestamp(belief)
        now = time.time()
        delta_t = max(0.0, now - last_verified)
        return math.exp(-self.config.recency_decay_rate * delta_t)

    def _resolve_last_verified_timestamp(self, belief: Any) -> float:
        """Resolve the last verified epoch timestamp from belief attributes."""
        for attr in (
            "timestamp_last_verified",
            "revised_at",
            "created_at",
            "latest_timestamp",
            "timestamp_created",
        ):
            val = getattr(belief, attr, None)
            parsed = self._parse_timestamp(val)
            if parsed is not None:
                return parsed

        # Check evidences
        evidences = getattr(belief, "evidences", None)
        if evidences:
            timestamps: list[float] = []
            for ev in evidences:
                ts = getattr(ev, "timestamp", None)
                parsed = self._parse_timestamp(ts)
                if parsed is not None:
                    timestamps.append(parsed)
            if timestamps:
                return max(timestamps)

        # Fallback to current time
        return time.time()

    def _parse_timestamp(self, val: Any) -> float | None:
        """Helper to parse raw attribute value into a float timestamp."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                # Standardize ISO 8601 UTC suffix for fromisoformat compatibility
                normalized = val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(normalized)
                return dt.timestamp()
            except ValueError:
                pass
        return None

    def _extract_token_cost(self, belief: Any) -> float:
        """Extract or estimate token cost of the belief."""
        cost = getattr(belief, "cost_tokens", None)
        if isinstance(cost, (int, float)):
            return float(cost)

        # Fallback estimation based on content length
        content = getattr(belief, "content", None)
        if content is None:
            # Check for value / payload if no direct content
            content = str(getattr(belief, "value", ""))

        return max(1.0, len(str(content)) / 4.0)
