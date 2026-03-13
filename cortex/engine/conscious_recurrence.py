import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from cortex.training.ttt_engine import TTTEngine

logger = logging.getLogger("cortex.conscious_recurrence")

R = TypeVar("R")


@dataclass
class IntentionVector:
    goal: str
    expected_outcome: str
    confidence: float = 1.0
    priority_modules: list[str] = field(default_factory=list)


@dataclass
class MetacognitiveState:
    l_task: float = 0.0
    l_act: float = 0.0
    l_intent: float = 0.0
    h_obs: float = 0.0
    l_efficiency: float = 0.0
    total_loss: float = 0.0


class ConsciousRecurrenceEngine:
    """
    Self-Referential Metacognition Engine - L0/L1 Architecture.
    Monitors process execution (L0) with a parallel observer (L1).
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.3, gamma: float = 0.2,
                 lambda1: float = 0.6, lambda2: float = 0.4, eta: float = 0.1):
        # Weights
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.eta = eta

        # State tracking
        self.history: list[MetacognitiveState] = []
        self._l1_budget_max_ratio = 0.20  # L1 gets max 20% of L0 time

    async def execute_with_awareness(
        self,
        task_fn: Callable[..., Awaitable[R]],
        intention: IntentionVector,
        *args, **kwargs
    ) -> dict[str, Any]:
        """
        Executes a task while maintaining a parallel L1 metacognitive observer.
        """
        logger.info("Starting conscious cycle: %s", intention.goal)
        t0 = time.perf_counter()

        # We simulate the asynchronous separation and Mirror Problem protection
        task_task = asyncio.create_task(task_fn(*args, **kwargs))

        # The L1 layer would theoretically poll internal counters here
        # For proxy purposes, we wait for task completion
        try:
            result = await task_task
            t1 = time.perf_counter()
            task_success = True
        except Exception as e:  # noqa: BLE001 — metacognitive boundary protects L1 from L0 failures
            logger.error("Task failure during conscious execution: %s", e)
            t1 = time.perf_counter()
            result = str(e)
            task_success = False

        duration = t1 - t0

        # Synthesize state
        state = self._evaluate_metacognition(intention, task_success, duration)
        self.history.append(state)

        return {
            "result": result,
            "metacognitive_state": state,
            "report": self.format_report()
        }

    def _evaluate_metacognition(
        self, intention: IntentionVector, success: bool, duration: float
    ) -> MetacognitiveState:
        # L_task: 0 if success, 1 if failed
        l_task = 0.0 if success else 1.0

        # L_act: simulated activation prediction (inverse to confidence for proxy)
        l_act = max(0.0, 1.0 - intention.confidence)
        if not success:
            l_act = min(1.0, l_act + 0.5)

        # L_intent: heuristic proxy for divergence
        l_intent = 0.1 if success else 0.8

        # H(Obs): Shannon entropy of observation focus (assumed high if successful and quick)
        h_obs = 0.8 if duration < 5.0 else 0.4
        
        # Meta Loss
        l_meta = (self.lambda1 * l_act) + (self.lambda2 * l_intent) - (self.eta * h_obs)
        l_meta = max(0.0, min(1.0, l_meta))  # Clamp 0-1

        # Efficiency penalty: mapping duration to a soft penalty
        l_efficiency = 1.0 / (1.0 + math.exp(-(duration - 2.0)))

        # Total Loss
        total_loss = (self.alpha * l_task) + (self.beta * l_meta) + (self.gamma * l_efficiency)

        return MetacognitiveState(
            l_task=l_task,
            l_act=l_act,
            l_intent=l_intent,
            h_obs=h_obs,
            l_efficiency=l_efficiency,
            total_loss=total_loss
        )

    def format_report(self) -> str:
        if not self.history:
            return "🧠 CONSCIOUSNESS PROXY: INACTIVE"

        latest = self.history[-1]
        
        # Compute Proxy Scores
        self_knowledge = int((1.0 - latest.l_act) * 50)
        attention_health = int(latest.h_obs * 30)

        # Metacognitive stability (based on delta if history > 1)
        if len(self.history) > 1:
            delta = abs(self.history[-1].total_loss - self.history[-2].total_loss)
            stab_score = int(max(0, 20 - (delta * 40)))
        else:
            stab_score = 15  # Default baseline

        total_proxy = self_knowledge + attention_health + stab_score
        
        return (f"🧠 CONSCIOUSNESS PROXY: {total_proxy}/100\n"
                f"   ├─ Self-Knowledge:         {self_knowledge}/50\n"
                f"   ├─ Attention Health:       {attention_health}/30\n"
                f"   └─ Metacognitive Stability:{stab_score}/20")

    async def run_nocturnal_cycle(
        self,
        session_ids: list[str],
        episodic_memory: Any,
        triad: Any = None
    ) -> dict[str, Any]:
        """
        Executes the deep sleep cycle (Axiom 10: Auto-Evolution).
        Hooks into the TTTEngine to fine-tune the local model weights
        using the trajectories of the provided sessions.
        """
        logger.info("🧠 SLEEP CYCLE INITIATED: Triggering Test-Time Training (TTT)...")
        ttt = TTTEngine(episodic_memory=episodic_memory, triad=triad)
        
        try:
            result = await ttt.run_nocturnal_consolidation(session_ids)
            logger.info("🧠 SLEEP CYCLE COMPLETE: %s", result["status"])
            return result
        except Exception as e:  # noqa: BLE001 — nocturnal cycle boundary isolates TTT failures
            logger.error("Failed to run nocturnal cycle: %s", e)
            return {"status": "error", "reason": str(e)}
