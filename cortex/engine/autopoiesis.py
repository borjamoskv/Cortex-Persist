"""
CORTEX V5 - Sovereign Autopoiesis Engine
Second-Order Cybernetics (Maturana / Varela): Axiom 10 Recursive Auto-Evolution.
"""

import ast
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any

from cortex.engine.endocrine import ENDOCRINE, HormoneType

logger = logging.getLogger("cortex.autopoiesis")


class AutopoiesisEngine:
    """
    A system that observes, understands, and rewrites itself at runtime.
    Not merely altering external systems, but mutating its own basal core.
    """

    def __init__(self, observation_window_ms: int = 100):
        self.observation_window_ms = observation_window_ms
        self._history: dict[str, dict[str, Any]] = {}

    def observe_and_mutate(self, func: Callable) -> Callable:
        """
        Decorator that tracks execution metrics of its own methods and dynamically
        rewrites the AST if consecutive degrading performance is detected.
        """
        func_name = func.__name__

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_t = time.perf_counter_ns()
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                result = e
                success = False

            latency_ms = (time.perf_counter_ns() - start_t) / 1e6

            self._record_observation(func_name, latency_ms, success)

            if self._requires_mutation(func_name):
                self._execute_autopoietic_rewrite(func)

            if not success and isinstance(result, Exception):
                raise result
            return result

        return wrapper

    def _record_observation(self, func_name: str, latency: float, success: bool) -> None:
        if func_name not in self._history:
            self._history[func_name] = {"latencies": [], "failures": 0}

        self._history[func_name]["latencies"].append(latency)
        if not success:
            self._history[func_name]["failures"] += 1
            ENDOCRINE.pulse(HormoneType.CORTISOL, 0.05)
        else:
            # Reward stability
            if latency < self.observation_window_ms:
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.01)
                ENDOCRINE.pulse(HormoneType.CORTISOL, -0.01)

        # O(1) bounded memory
        if len(self._history[func_name]["latencies"]) > 100:
            self._history[func_name]["latencies"].pop(0)

    def _requires_mutation(self, func_name: str) -> bool:
        stats = self._history.get(func_name)
        if not stats:
            return False

        lats = stats["latencies"]
        if len(lats) < 10:
            return False

        # If the last 5 latencies are consistently > 2x the historical average
        historical_avg = sum(lats[:-5]) / max(len(lats[:-5]), 1)
        recent_avg = sum(lats[-5:]) / 5.0

        if recent_avg > (historical_avg * 2.0) and recent_avg > self.observation_window_ms:
            return True
        return False

    def _execute_autopoietic_rewrite(self, func: Callable) -> None:
        """
        The core of autopoiesis. Re-evaluates the function's AST and attempts
        JIT recompilation or structural modification to adapt to new load patterns.
        """
        logger.warning(f"AUTOPOIESIS TRIGGERED: Structural mutation initiated for {func.__name__}")
        try:
            source = inspect.getsource(func)
            ast.parse(source)  # Validate AST; future: DEMIURGE-OMEGA integration
            # In a full implementation, this integrates with DEMIURGE-OMEGA to
            # replace O(N) loops with O(1) lookups and re-bind native extensions.
            logger.info("AST captured. Awaiting Demiurge compilation bridge.")

            # Reset history to allow new form to stabilize
            self._history[func.__name__] = {"latencies": [], "failures": 0}
        except TypeError:
            logger.error("Function source unavailable for mutation.")
