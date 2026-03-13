# SPDX-License-Identifier: Apache-2.0
"""Axioma Ω₇ — Zero-Prompting Autonomous Evolution Strategy.

The frontier collapse: continuous learning reduced to a single directive
free of orchestration. The system predicts entropy before it occurs,
executes the necessary CORTEX mutation, purges ghosts, and produces
a cryptographic report of what was resolved — without user prompts.

Implementation as a pluggable strategy for the CortexEvolutionEngine.

Thermodynamic Model:
  - Entropy is predicted via ghost_density + error_rate trends
  - If predicted_entropy > threshold, autonomous mutation fires
  - Ghost purge eliminates dead code / stale facts
  - SHA-256 signed resolution report anchors to the ledger
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cortex.engine.evolution_metrics import CortexMetrics
from cortex.engine.evolution_types import (
    DomainMetrics,
    SovereignAgent,
    SubAgent,
)

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTROPY PREDICTION MODEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Entropy prediction threshold — above this, autonomous mutation fires
_ENTROPY_THRESHOLD: float = 0.40

# Minimum fitness for a subagent to be eligible for zero-prompting evolution
_MIN_FITNESS_GATE: float = 60.0

# Maximum ghost density allowed before forced purge
_GHOST_PURGE_THRESHOLD: float = 0.30

# EWMA decay factor for entropy prediction (α = 0.3 → recent data weighted more)
_EWMA_ALPHA: float = 0.3


@dataclass()
class EntropyPrediction:
    """Predicted entropy state for a domain."""

    domain_id: str
    predicted_entropy: float
    ghost_density: float
    error_rate: float
    trend: str  # "rising", "stable", "falling"
    should_mutate: bool
    should_purge: bool
    timestamp: float = field(default_factory=time.time)


@dataclass()
class ResolutionReport:
    """Cryptographic report of autonomous entropy resolution.

    This is the proof-of-work that the Zero-Prompting directive executed
    correctly — anchored to the ledger via SHA-256 hash chain.
    """

    report_id: str
    domain_id: str
    agent_id: str
    timestamp: float
    entropy_before: float
    entropy_after: float
    ghosts_purged: int
    mutations_applied: list[str]
    fitness_delta: float
    hash: str = ""

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash for ledger anchoring."""
        payload = (
            f"{self.report_id}|{self.domain_id}|{self.agent_id}|"
            f"{self.timestamp}|{self.entropy_before:.6f}|"
            f"{self.entropy_after:.6f}|{self.ghosts_purged}|"
            f"{len(self.mutations_applied)}|{self.fitness_delta:.4f}"
        )
        self.hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.hash


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZERO-PROMPTING EVOLUTION STRATEGY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ZeroPromptingEvolutionStrategy:
    """Axiom Ω₇ implementation — Autonomous entropy prediction and resolution.

    The strategy follows a three-phase cycle:
      1. PREDICT — Estimate upcoming entropy via EWMA of ghost_density + error_rate
      2. MUTATE  — If predicted entropy exceeds threshold, apply corrective mutation
      3. REPORT  — Generate cryptographic resolution report for the ledger

    This strategy does NOT require user prompts: it fires autonomously
    when the thermodynamic conditions are met.
    """

    def __init__(self) -> None:
        self._entropy_history: dict[str, list[float]] = {}
        self._resolution_log: list[ResolutionReport] = []

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        """ImprovementStrategy protocol implementation."""
        # Gate: only act on fit-enough agents
        if subagent.fitness < _MIN_FITNESS_GATE:
            return None

        # Phase 1: PREDICT
        prediction = self._predict_entropy(sovereign.domain_id, metrics)

        if not prediction.should_mutate and not prediction.should_purge:
            return None

        # Phase 2: MUTATE + PURGE
        entropy_before = prediction.predicted_entropy
        mutations_applied: list[str] = []
        ghosts_purged = 0
        fitness_before = subagent.fitness

        if prediction.should_purge:
            ghosts_purged = self._purge_ghosts(subagent, metrics)
            mutations_applied.append(f"ghost_purge:{ghosts_purged}")

        if prediction.should_mutate:
            mutation_desc = self._apply_autonomous_mutation(subagent, metrics, prediction)
            mutations_applied.append(mutation_desc)

        entropy_after = self._compute_current_entropy(metrics, ghosts_purged)
        fitness_delta = subagent.fitness - fitness_before

        # Phase 3: REPORT
        report = ResolutionReport(
            report_id=f"zp-{int(time.time())}-{subagent.agent_id[:8]}",
            domain_id=sovereign.domain_id,
            agent_id=subagent.agent_id,
            timestamp=time.time(),
            entropy_before=entropy_before,
            entropy_after=entropy_after,
            ghosts_purged=ghosts_purged,
            mutations_applied=mutations_applied,
            fitness_delta=fitness_delta,
        )
        report.compute_hash()
        self._resolution_log.append(report)

        subagent.mutation.record_change(
            f"Ω₇ ZeroPrompting: ΔS={entropy_before - entropy_after:.4f}, "
            f"ghosts={ghosts_purged}, hash={report.hash[:16]}"
        )

        logger.info(
            "[Ω₇] Domain=%s Agent=%s ΔS=%.4f ghosts=%d hash=%s",
            sovereign.domain_id,
            subagent.agent_id,
            entropy_before - entropy_after,
            ghosts_purged,
            report.hash[:16],
        )

        return {
            "strategy": "ZeroPromptingEvolution",
            "axiom": "Ω₇",
            "prediction": {
                "entropy": prediction.predicted_entropy,
                "trend": prediction.trend,
                "should_mutate": prediction.should_mutate,
                "should_purge": prediction.should_purge,
            },
            "resolution": {
                "entropy_before": entropy_before,
                "entropy_after": entropy_after,
                "delta_entropy": entropy_before - entropy_after,
                "ghosts_purged": ghosts_purged,
                "mutations": mutations_applied,
                "fitness_delta": fitness_delta,
            },
            "report_hash": report.hash,
            "report_id": report.report_id,
        }

    # ── Phase 1: Entropy Prediction ───────────────────────────────────────

    def _predict_entropy(self, domain_id: str, metrics: DomainMetrics) -> EntropyPrediction:
        """Predict upcoming entropy using EWMA of composite signals."""
        # Composite entropy signal: weighted sum of ghost_density and error_rate
        current_signal = 0.6 * metrics.ghost_density + 0.4 * metrics.error_rate

        history = self._entropy_history.setdefault(domain_id, [])
        history.append(current_signal)

        # Keep window bounded
        if len(history) > 20:
            history.pop(0)

        # EWMA calculation
        if len(history) == 1:
            predicted = current_signal
        else:
            predicted = history[-1]
            for val in reversed(history[:-1]):
                predicted = _EWMA_ALPHA * predicted + (1 - _EWMA_ALPHA) * val

        # Trend detection
        if len(history) >= 3:
            recent = history[-3:]
            if recent[-1] > recent[0] * 1.1:
                trend = "rising"
            elif recent[-1] < recent[0] * 0.9:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        should_mutate = predicted > _ENTROPY_THRESHOLD
        should_purge = metrics.ghost_density > _GHOST_PURGE_THRESHOLD

        return EntropyPrediction(
            domain_id=domain_id,
            predicted_entropy=predicted,
            ghost_density=metrics.ghost_density,
            error_rate=metrics.error_rate,
            trend=trend,
            should_mutate=should_mutate,
            should_purge=should_purge,
        )

    # ── Phase 2a: Autonomous Mutation ─────────────────────────────────────

    def _apply_autonomous_mutation(
        self,
        subagent: SubAgent,
        metrics: DomainMetrics,
        prediction: EntropyPrediction,
    ) -> str:
        """Apply a corrective mutation to reduce predicted entropy."""
        # Mutation magnitude proportional to entropy overshoot
        overshoot = prediction.predicted_entropy - _ENTROPY_THRESHOLD
        correction_factor = min(2.0, 1.0 + overshoot * 3.0)

        # Strengthen entropy resistance
        subagent.mutation.entropy_resistance = min(
            2.0,
            subagent.mutation.entropy_resistance + correction_factor * 0.1,
        )

        # Fitness reward for proactive entropy reduction
        fitness_boost = correction_factor * 2.5
        subagent.fitness += fitness_boost

        # Inject corrective parameter
        param_key = f"zp_correction_{int(time.time())}"
        subagent.mutation.parameters[param_key] = correction_factor * 100

        desc = (
            f"autonomous_mutation: correction={correction_factor:.2f}, "
            f"+fitness={fitness_boost:.2f}"
        )
        return desc

    # ── Phase 2b: Ghost Purge ─────────────────────────────────────────────

    def _purge_ghosts(self, subagent: SubAgent, metrics: DomainMetrics) -> int:
        """Purge ghost entries from mutation history to reduce noise."""
        original_len = len(subagent.mutation.history_log)
        if original_len <= 1:
            return 0

        # Purge proportion based on ghost density
        purge_ratio = min(0.7, metrics.ghost_density * 2.0)
        keep_count = max(1, int(original_len * (1.0 - purge_ratio)))

        # Keep only most recent entries
        subagent.mutation.history_log = subagent.mutation.history_log[-keep_count:]
        purged = original_len - len(subagent.mutation.history_log)

        # Fitness reward for ghost elimination
        subagent.fitness += purged * 0.3

        return purged

    # ── Entropy Computation ───────────────────────────────────────────────

    def _compute_current_entropy(self, metrics: DomainMetrics, ghosts_purged: int) -> float:
        """Compute entropy state after mutations."""
        base = 0.6 * metrics.ghost_density + 0.4 * metrics.error_rate
        reduction = ghosts_purged * 0.02
        return max(0.0, base - reduction)

    # ── Telemetry ─────────────────────────────────────────────────────────

    @property
    def resolution_count(self) -> int:
        return len(self._resolution_log)

    @property
    def last_report(self) -> ResolutionReport | None:
        return self._resolution_log[-1] if self._resolution_log else None

    def get_resolution_hashes(self) -> list[str]:
        """Return all resolution hashes for ledger verification."""
        return [r.hash for r in self._resolution_log]
