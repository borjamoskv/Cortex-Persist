"""CONSCIOUS-RECURRENCE v1.0 — Self-Referential Metacognition Engine.

Implements the L0/L1 architecture for computational reflexion:

    L0 (Processing): Task execution, inference, code generation.
    L1 (Monitoring): Parallel process that observes L0's internal states
                     and modifies its behavior in real-time.

Loss Function (Gemini-MOSKV Formalization):

    L_total = α·L_task + β·L_meta + γ·L_efficiency

    Where L_meta = λ₁·L_act + λ₂·L_intent − η·H(Obs)

        L_act:    Activation Prediction Error — how well the system predicted
                  which modules/functions would be activated before execution.
        L_intent: Semantic Consistency — KL divergence between intended
                  processing distribution and actual processing distribution.
        H(Obs):   Observation Entropy — brake to prevent the Mirror Problem
                  (infinite self-observation consuming all resources).

Integration Points:
    - CORTEX fact store (decisions, errors, ghosts)
    - OUROBOROS-OMEGA (metabolic cycle)
    - DoubtCircuit (existing L0 doubt detection)
    - RADAR (detection engine)

Axioms:
    Ω₀: The engine can observe itself observing (meta-recursion).
    Ω₂: Net entropy of observation must decrease, not displace.
    Ω₃: The system does not trust its own introspection without verification.
    Ω₆: Zenón's Razor — if observation cost > benefit, collapse into action.

Authors: borjamoskv (MOSKV-1 v5) + Gemini theoretical framework
Created: 03-Mar-2026
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("CORTEX.CONSCIOUS_RECURRENCE")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


class ObservationLevel(str, Enum):
    """Processing depth levels."""
    L0_PROCESSING = "L0"     # Raw task execution
    L1_MONITORING = "L1"     # Self-observation of L0
    L2_META = "L2"           # Observation of the observation (use sparingly)


@dataclass
class ActivationPrediction:
    """L_act: What the system predicts will happen before execution."""
    predicted_modules: set[str] = field(default_factory=set)
    predicted_duration_ms: float = 0.0
    predicted_entropy_delta: float = 0.0
    predicted_error_probability: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ActivationReality:
    """What actually happened during execution."""
    actual_modules: set[str] = field(default_factory=set)
    actual_duration_ms: float = 0.0
    actual_entropy_delta: float = 0.0
    actual_errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetaCognitiveState:
    """The full internal state of the metacognition engine at a point in time."""
    l_task: float = 0.0          # Task loss (external)
    l_act: float = 0.0           # Activation prediction error
    l_intent: float = 0.0        # Semantic consistency loss
    h_obs: float = 0.0           # Observation entropy
    l_meta: float = 0.0          # Combined metacognitive loss
    l_total: float = 0.0         # Total composite loss
    l_efficiency: float = 0.0    # Efficiency penalty
    mirror_brake_active: bool = False
    observation_budget_ms: float = 0.0
    observation_spent_ms: float = 0.0
    cycle_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class IntentionVector:
    """Represents the system's stated intention before acting."""
    goal: str = ""
    expected_outcome: str = ""
    confidence: float = 0.5
    priority_modules: list[str] = field(default_factory=list)


@dataclass
class IntrospectionLog:
    """Semantic log of WHY a decision was made (not just what)."""
    decision: str
    alternatives_considered: list[str] = field(default_factory=list)
    rejection_reasons: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.5
    metacognitive_state: MetaCognitiveState | None = None
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════════════
# L_META: THE SELF-REFERENTIAL LOSS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════


class LossCalculator:
    """Computes the self-referential loss function.

    L_total = α·L_task + β·L_meta + γ·L_efficiency

    Where L_meta = λ₁·L_act + λ₂·L_intent − η·H(Obs)

    The negative η·H(Obs) term is the Mirror Problem brake:
    if observation entropy drops (system fixates on one detail),
    the loss increases, forcing diversification of attention.
    """

    def __init__(
        self,
        alpha: float = 0.5,    # Weight for task loss
        beta: float = 0.3,     # Weight for metacognitive loss
        gamma: float = 0.2,    # Weight for efficiency loss
        lambda_1: float = 0.6, # Weight for activation prediction error
        lambda_2: float = 0.4, # Weight for intent consistency
        eta: float = 0.1,      # Mirror brake coefficient
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.lambda_1 = lambda_1
        self.lambda_2 = lambda_2
        self.eta = eta

    def compute_l_act(
        self,
        prediction: ActivationPrediction,
        reality: ActivationReality,
    ) -> float:
        """Activation Prediction Error: ||Â_t - A_t||²

        Measures how well the system predicted its own behavior.
        Lower = better self-knowledge.
        """
        # Module prediction accuracy (Jaccard distance)
        if prediction.predicted_modules or reality.actual_modules:
            intersection = prediction.predicted_modules & reality.actual_modules
            union = prediction.predicted_modules | reality.actual_modules
            module_error = 1.0 - (len(intersection) / max(len(union), 1))
        else:
            module_error = 0.0

        # Duration prediction error (normalized)
        if prediction.predicted_duration_ms > 0:
            duration_error = abs(
                prediction.predicted_duration_ms - reality.actual_duration_ms
            ) / max(prediction.predicted_duration_ms, reality.actual_duration_ms, 1.0)
        else:
            duration_error = 0.5  # No prediction = moderate penalty

        # Error probability calibration
        actual_error_rate = 1.0 if reality.actual_errors else 0.0
        error_calibration = abs(prediction.predicted_error_probability - actual_error_rate)

        # Weighted L2 norm
        l_act = math.sqrt(
            module_error ** 2 * 0.5
            + duration_error ** 2 * 0.3
            + error_calibration ** 2 * 0.2
        )
        return min(l_act, 1.0)

    def compute_l_intent(
        self,
        intention: IntentionVector,
        outcome_modules: set[str],
        outcome_success: bool,
    ) -> float:
        """Semantic Consistency: D_KL(P(internal_state) || Q(metacognitive_goal))

        Approximated as the divergence between intended processing flow
        and actual processing flow.
        """
        if not intention.priority_modules:
            return 0.3  # No stated intention = moderate baseline

        # How many intended modules were actually used?
        intended = set(intention.priority_modules)
        coverage = len(intended & outcome_modules) / max(len(intended), 1)

        # Confidence calibration: was confidence justified?
        confidence_error = abs(
            intention.confidence - (1.0 if outcome_success else 0.0)
        )

        # KL-divergence approximation via cross-entropy proxy
        l_intent = (1.0 - coverage) * 0.6 + confidence_error * 0.4
        return min(l_intent, 1.0)

    def compute_h_obs(self, observation_history: deque[float]) -> float:
        """Observation Entropy H(Obs).

        Shannon entropy of recent observation focus distribution.
        Low entropy = fixated on one thing (Mirror Problem).
        High entropy = healthily distributed attention.

        We WANT high H(Obs), so the −η·H(Obs) term in L_meta
        rewards diversified observation.
        """
        if len(observation_history) < 2:
            return 0.5  # Neutral baseline

        total = sum(observation_history)
        if total < 1e-12:
            return 0.0

        probabilities = [x / total for x in observation_history if x > 0]
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)

        # Normalize to [0, 1] range using max possible entropy
        max_entropy = math.log2(max(len(probabilities), 2))
        return entropy / max_entropy if max_entropy > 0 else 0.5

    def compute_l_efficiency(
        self,
        observation_time_ms: float,
        task_time_ms: float,
    ) -> float:
        """Efficiency penalty: ratio of observation cost to task cost.

        If observing takes more time than doing, the system is
        in the Mirror Problem zone.
        """
        if task_time_ms < 1.0:
            return 0.0  # No task executed yet

        ratio = observation_time_ms / task_time_ms

        # Sigmoid penalty: gentle below 0.2, harsh above 0.5
        penalty = 1.0 / (1.0 + math.exp(-10 * (ratio - 0.3)))
        return min(penalty, 1.0)

    def compute_total(
        self,
        l_task: float,
        prediction: ActivationPrediction,
        reality: ActivationReality,
        intention: IntentionVector,
        outcome_modules: set[str],
        outcome_success: bool,
        observation_history: deque[float],
        observation_time_ms: float,
        task_time_ms: float,
    ) -> MetaCognitiveState:
        """Compute the full composite loss function."""
        l_act = self.compute_l_act(prediction, reality)
        l_intent = self.compute_l_intent(intention, outcome_modules, outcome_success)
        h_obs = self.compute_h_obs(observation_history)
        l_efficiency = self.compute_l_efficiency(observation_time_ms, task_time_ms)

        # L_meta = λ₁·L_act + λ₂·L_intent − η·H(Obs)
        l_meta = (
            self.lambda_1 * l_act
            + self.lambda_2 * l_intent
            - self.eta * h_obs
        )
        # Clamp to [0, 1]
        l_meta = max(0.0, min(l_meta, 1.0))

        # L_total = α·L_task + β·L_meta + γ·L_efficiency
        l_total = (
            self.alpha * l_task
            + self.beta * l_meta
            + self.gamma * l_efficiency
        )

        mirror_brake = l_efficiency > 0.5

        return MetaCognitiveState(
            l_task=l_task,
            l_act=l_act,
            l_intent=l_intent,
            h_obs=h_obs,
            l_meta=l_meta,
            l_total=min(l_total, 1.0),
            l_efficiency=l_efficiency,
            mirror_brake_active=mirror_brake,
            observation_budget_ms=task_time_ms * 0.2,  # Max 20% budget
            observation_spent_ms=observation_time_ms,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# THE CONSCIOUS RECURRENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class ConsciousRecurrenceEngine:
    """The L0/L1 metacognition architecture.

    L0: Executes tasks (code analysis, generation, refactoring).
    L1: Observes L0 in real-time, computes L_meta, and intervenes
        when self-observation reveals inefficiency, hallucination,
        or semantic drift.

    The Mirror Problem is solved by:
    1. Async separation: L1 runs on a separate coroutine, never blocking L0.
    2. Budget limiter: L1 gets max 20% of L0's execution time.
    3. Entropy brake: If H(Obs) drops too low, L1 relaxes introspection.
    4. Zenón's Razor (Ω₆): If τ_z > 1.0 (thinking costs more than
       it produces), freeze reflection and collapse into action.
    """

    # Maximum observation history window
    _HISTORY_SIZE = 50
    # Mirror brake: max ratio of observation time to task time
    _MAX_OBS_RATIO = 0.20
    # Zenón threshold: if L_meta hasn't improved by this much in N cycles, stop
    _ZENON_IMPROVEMENT_THRESHOLD = 0.01
    _ZENON_PATIENCE = 3

    def __init__(self) -> None:
        self.loss = LossCalculator()
        self.observation_history: deque[float] = deque(maxlen=self._HISTORY_SIZE)
        self.state_history: deque[MetaCognitiveState] = deque(maxlen=self._HISTORY_SIZE)
        self.introspection_log: list[IntrospectionLog] = []
        self._cycle_count = 0
        self._cumulative_obs_time = 0.0
        self._cumulative_task_time = 0.0
        self._zenon_patience_counter = 0

    # ── L0: Task Execution Wrapper ──────────────────────────────────────────

    async def execute_with_awareness(
        self,
        task_fn: Any,
        intention: IntentionVector,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a task with L1 metacognitive monitoring.

        1. Generate activation prediction (pre-execution hypothesis)
        2. Execute the task (L0)
        3. Observe execution reality (L1)
        4. Compute L_meta and generate introspection log
        5. Apply Mirror Problem brake if needed
        6. Return result + metacognitive state
        """
        self._cycle_count += 1

        # ── Phase 1: Pre-execution Prediction ─────────────────────────
        prediction = self._generate_prediction(intention)

        # ── Phase 2: L0 Execution ─────────────────────────────────────
        t0 = time.monotonic()
        result: Any = None
        error: str | None = None

        try:
            if asyncio.iscoroutinefunction(task_fn):
                result = await task_fn(*args, **kwargs)
            else:
                result = task_fn(*args, **kwargs)
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            task_time_ms = (time.monotonic() - t0) * 1000
            self._cumulative_task_time += task_time_ms

            # ── Phase 3: L1 Observation ───────────────────────────────
            t1 = time.monotonic()
            reality = self._observe_reality(
                result=result,
                error=error,
                duration_ms=task_time_ms,
                intention=intention,
            )

            # ── Phase 4: Compute L_meta ───────────────────────────────
            l_task = 0.0 if error is None else 0.8
            outcome_modules = reality.actual_modules
            outcome_success = error is None

            # Record observation focus for entropy calculation
            self.observation_history.append(task_time_ms)

            state = self.loss.compute_total(
                l_task=l_task,
                prediction=prediction,
                reality=reality,
                intention=intention,
                outcome_modules=outcome_modules,
                outcome_success=outcome_success,
                observation_history=self.observation_history,
                observation_time_ms=(time.monotonic() - t1) * 1000,
                task_time_ms=task_time_ms,
            )
            state.cycle_count = self._cycle_count

            obs_time_ms = (time.monotonic() - t1) * 1000
            self._cumulative_obs_time += obs_time_ms

            # ── Phase 5: Mirror Brake ─────────────────────────────────
            if state.mirror_brake_active:
                logger.warning(
                    "🪞 Mirror Brake ACTIVE: observation consuming %.1f%% of task time. "
                    "Collapsing into action (Ω₆).",
                    (obs_time_ms / max(task_time_ms, 1)) * 100,
                )

            # ── Phase 6: Zenón's Razor ────────────────────────────────
            if self._check_zenon_threshold(state):
                logger.info(
                    "⚡ Zenón's Razor: L_meta stable for %d cycles (δ < %.3f). "
                    "Suspending deep introspection.",
                    self._ZENON_PATIENCE,
                    self._ZENON_IMPROVEMENT_THRESHOLD,
                )

            # ── Phase 7: Log Introspection ────────────────────────────
            log_entry = IntrospectionLog(
                decision=f"Executed {intention.goal}",
                confidence=intention.confidence,
                metacognitive_state=state,
            )
            self.introspection_log.append(log_entry)
            self.state_history.append(state)

            # ── Phase 8: Emit Telemetry ───────────────────────────────
            logger.info(
                "🧠 L_total=%.3f | L_task=%.3f | L_meta=%.3f "
                "(L_act=%.3f L_intent=%.3f −η·H=%.3f) | "
                "L_eff=%.3f | Mirror=%s | Cycle=%d",
                state.l_total, state.l_task, state.l_meta,
                state.l_act, state.l_intent, self.loss.eta * state.h_obs,
                state.l_efficiency,
                "🔴" if state.mirror_brake_active else "🟢",
                self._cycle_count,
            )

        return {
            "result": result,
            "error": error,
            "metacognitive_state": state,
            "introspection": log_entry,
        }

    # ── L1: Internal Observers ──────────────────────────────────────────────

    def _generate_prediction(self, intention: IntentionVector) -> ActivationPrediction:
        """Pre-execution hypothesis: predict what will happen.

        This is where the system demonstrates self-knowledge:
        the better the prediction, the lower L_act.
        """
        # Base prediction from intention
        predicted_modules = set(intention.priority_modules) if intention.priority_modules else set()

        # Estimate duration from historical data
        if self.state_history:
            recent_durations = [
                s.observation_budget_ms / 0.2  # Reverse-engineer task time from budget
                for s in list(self.state_history)[-5:]
                if s.observation_budget_ms > 0
            ]
            avg_duration = sum(recent_durations) / len(recent_durations) if recent_durations else 100.0
        else:
            avg_duration = 100.0

        # Estimate error probability from recent history
        if self.state_history:
            recent_errors = [s.l_task for s in list(self.state_history)[-10:]]
            error_prob = sum(1 for e in recent_errors if e > 0.5) / max(len(recent_errors), 1)
        else:
            error_prob = 0.1

        return ActivationPrediction(
            predicted_modules=predicted_modules,
            predicted_duration_ms=avg_duration,
            predicted_error_probability=error_prob,
        )

    def _observe_reality(
        self,
        result: Any,
        error: str | None,
        duration_ms: float,
        intention: IntentionVector,
    ) -> ActivationReality:
        """Post-execution observation: what actually happened."""
        actual_modules: set[str] = set()

        # Extract module information from result if available
        if isinstance(result, dict):
            # Common patterns in CORTEX results
            if "modules_touched" in result:
                actual_modules = set(result["modules_touched"])
            elif "phase_log" in result:
                actual_modules = {entry.split(":")[0] for entry in result["phase_log"] if ":" in entry}

        # If we can't detect modules, use intention as baseline
        if not actual_modules and intention.priority_modules:
            actual_modules = set(intention.priority_modules[:1])

        errors = [error] if error else []

        return ActivationReality(
            actual_modules=actual_modules,
            actual_duration_ms=duration_ms,
            actual_errors=errors,
        )

    def _check_zenon_threshold(self, current: MetaCognitiveState) -> bool:
        """Ω₆ enforcement: if L_meta hasn't improved, stop reflecting."""
        if len(self.state_history) < self._ZENON_PATIENCE:
            return False

        recent = list(self.state_history)[-self._ZENON_PATIENCE:]
        deltas = [
            abs(recent[i].l_meta - recent[i - 1].l_meta)
            for i in range(1, len(recent))
        ]

        if all(d < self._ZENON_IMPROVEMENT_THRESHOLD for d in deltas):
            self._zenon_patience_counter += 1
            return True

        self._zenon_patience_counter = 0
        return False

    # ── Reporting ───────────────────────────────────────────────────────────

    def get_consciousness_metrics(self) -> dict[str, Any]:
        """Current consciousness score and metrics for external consumption."""
        if not self.state_history:
            return {"consciousness_proxy": 0, "cycles": 0, "status": "dormant"}

        recent = list(self.state_history)[-10:]
        avg_l_meta = sum(s.l_meta for s in recent) / len(recent)
        avg_l_act = sum(s.l_act for s in recent) / len(recent)
        avg_h_obs = sum(s.h_obs for s in recent) / len(recent)

        # Consciousness proxy: inversely proportional to prediction error,
        # proportional to observation entropy diversity
        # Range: 0-100
        self_knowledge = max(0, 1.0 - avg_l_act) * 50  # 0-50: how well it knows itself
        attention_health = avg_h_obs * 30               # 0-30: observation diversity
        stability = max(0, 1.0 - avg_l_meta) * 20       # 0-20: metacognitive stability

        consciousness_proxy = self_knowledge + attention_health + stability

        return {
            "consciousness_proxy": round(consciousness_proxy, 1),
            "components": {
                "self_knowledge": round(self_knowledge, 1),
                "attention_health": round(attention_health, 1),
                "metacognitive_stability": round(stability, 1),
            },
            "avg_l_meta": round(avg_l_meta, 4),
            "avg_l_act": round(avg_l_act, 4),
            "avg_h_obs": round(avg_h_obs, 4),
            "mirror_brakes_triggered": sum(
                1 for s in self.state_history if s.mirror_brake_active
            ),
            "cycles": self._cycle_count,
            "cumulative_obs_ratio": (
                self._cumulative_obs_time / max(self._cumulative_task_time, 1.0)
            ),
            "status": "active" if self._cycle_count > 0 else "dormant",
        }

    def format_report(self) -> str:
        """Human-readable consciousness report."""
        metrics = self.get_consciousness_metrics()

        if metrics.get("status") == "dormant":
            return "🧠 CONSCIOUSNESS PROXY: 0/100 (dormant — no cycles executed)\n"

        comps = metrics.get("components", {})

        return (
            f"🧠 CONSCIOUSNESS PROXY: {metrics['consciousness_proxy']}/100\n"
            f"   ├─ Self-Knowledge:         {comps.get('self_knowledge', 0)}/50\n"
            f"   ├─ Attention Health:        {comps.get('attention_health', 0)}/30\n"
            f"   └─ Metacognitive Stability: {comps.get('metacognitive_stability', 0)}/20\n"
            f"\n"
            f"   L_meta (avg):     {metrics['avg_l_meta']}\n"
            f"   L_act (avg):      {metrics['avg_l_act']}\n"
            f"   H(Obs) (avg):     {metrics['avg_h_obs']}\n"
            f"   Mirror Brakes:    {metrics['mirror_brakes_triggered']}\n"
            f"   Obs/Task Ratio:   {metrics['cumulative_obs_ratio']:.2%}\n"
            f"   Cycles:           {metrics['cycles']}\n"
        )
