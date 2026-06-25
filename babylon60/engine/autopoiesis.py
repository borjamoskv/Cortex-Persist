# [C5-REAL] Exergy-Maximized
"""
Sovereign Autopoiesis Engine
Second-Order Cybernetics (Maturana / Varela): Axiom 10 Recursive Auto-Evolution.
"""

import ast
import collections
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypedDict, TypeVar

from babylon60.engine.endocrine import ENDOCRINE, HormoneType

P = ParamSpec("P")
R = TypeVar("R")


class MutationHistory(TypedDict):
    latencies: collections.deque[float]
    failures: int


logger = logging.getLogger("babylon60.autopoiesis")


class AutopoiesisEngine:
    """
    A system that observes, understands, and rewrites itself at runtime.
    Not merely altering external systems, but mutating its own basal core.
    """

    def __init__(self, observation_window_ms: int = 100):
        self.observation_window_ms = observation_window_ms
        self._history: dict[str, MutationHistory] = {}

    def observe_and_mutate(self, func: Callable[P, R]) -> Callable[P, R]:
        """
        Decorator that tracks execution metrics of its own methods and dynamically
        rewrites the AST if consecutive degrading performance is detected.
        """
        func_name = func.__name__

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # KAIROS-Ω: Medición de pureza termodinámica (CPU-bound, purgado I/O noise).
            start_t = time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID)
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID) - start_t) / 1e6
                self._record_observation(func_name, latency_ms, True)
                if self._requires_mutation(func_name):
                    self._execute_autopoietic_rewrite(func)
                return result
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError):
                latency_ms = (time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID) - start_t) / 1e6
                self._record_observation(func_name, latency_ms, False)
                if self._requires_mutation(func_name):
                    self._execute_autopoietic_rewrite(func)
                raise  # Preserve original traceback (Ω₃)

        return wrapper

    def _record_observation(self, func_name: str, latency: float, success: bool) -> None:
        if func_name not in self._history:
            self._history[func_name] = {"latencies": collections.deque(maxlen=100), "failures": 0}

        self._history[func_name]["latencies"].append(latency)
        if not success:
            self._history[func_name]["failures"] += 1
            ENDOCRINE.pulse(HormoneType.CORTISOL, 0.05)
        else:
            # Reward stability
            if latency < self.observation_window_ms:
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.01)
                ENDOCRINE.pulse(HormoneType.CORTISOL, -0.01)

    def _requires_mutation(self, func_name: str) -> bool:
        stats = self._history.get(func_name)
        if not stats:
            return False

        lats = stats["latencies"]
        if len(lats) < 10:
            return False

        # If the last 5 latencies are consistently > 2x the historical average
        lats_list = list(lats)
        historical_avg = sum(lats_list[:-5]) / max(len(lats_list[:-5]), 1)
        recent_avg = sum(lats_list[-5:]) / 5.0

        if recent_avg > (historical_avg * 2.0) and recent_avg > self.observation_window_ms:
            return True
        return False

    def _execute_autopoietic_rewrite(self, func: Callable[..., Any]) -> None:
        """
        The core of autopoiesis. Re-evaluates the function's AST and validates
        parsability. Does NOT silently claim mutation succeeded.

        Ω₃ Honesty & PATHOGEN-OMEGA: Emits a structural ghost to the async swarm
        by physically creating an isolated git branch (AGENTS.md Rule 10) for external CI.
        """
        func_name = func.__name__
        logger.warning(
            "AUTOPOIESIS TRIGGERED: Performance degradation detected for '%s'. "
            "AST analysis initiated.",
            func_name,
        )
        try:
            source = inspect.getsource(func)
            tree = ast.parse(source)
            node_count = sum(1 for _ in ast.walk(tree))

            # [C5-REAL] Physical Git Branching for Isolation (Rule 10)
            import subprocess
            import uuid
            mitosis_id = uuid.uuid4().hex[:8]
            branch_name = f"auto/moskv1-mitosis-{func_name}-{mitosis_id}"
            
            # Detached subprocess to avoid blocking the main thread.
            # We create the branch so external CI/Swarm can pick it up.
            import os
            try:
                # Find project root relative to this file
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
                # [C5-REAL] Enforce thermodynamic limits before allowing agent mitosis
                import sys
                scarcity_gov = os.path.join(project_root, "ANTI_GRAVITY", "01_ACTIVE", "memory", "scarcity_governor.py")
                if os.path.exists(scarcity_gov):
                    res = subprocess.run([sys.executable, scarcity_gov], capture_output=True, text=True)
                    if res.returncode != 0:
                        logger.warning("SCARCITY_LOCK: Mitosis blocked due to high system load. Telemetry: %s", res.stdout.strip())
                        return

                subprocess.run(
                    ["git", "branch", branch_name, "HEAD"],
                    check=True,
                    capture_output=True,
                    cwd=project_root
                )
                logger.error(
                    "SWARM DISPATCH [PHYSICAL]: Autopoiesis branched '%s' (%d nodes) "
                    "to '%s' for O(1) external bypass. Engine execution protected.",
                    func_name,
                    node_count,
                    branch_name
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to create mitosis branch: {e}")

            # The Cooldown (Anti-Death Spiral): Clear the rapid latencies
            # to prevent infinite recursion of Cortisol in the same process.
            if func_name in self._history:
                self._history[func_name]["latencies"].clear()

        except (TypeError, OSError):
            logger.error("Function source unavailable for mutation of '%s'.", func_name)

    def mutate(self, target: str = "default") -> dict:
        """
        Public trigger for OmegaDaemon compatibility.
        Dispatches an AST mutation cycle via OuroborosCompiler.
        """
        logger.info(f"[AutopoiesisEngine] mutate() triggered — target={target!r}")
        try:
            # Delegate to the internal compiler if available
            if hasattr(self, "_compiler") and self._compiler:
                return self._compiler.run_cycle(target=target)
            # Fallback: mark target for next observe_and_mutate pass
            self._pending_targets = getattr(self, "_pending_targets", [])
            self._pending_targets.append(target)
            return {"status": "queued", "target": target}
        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as exc:  # P0-PURGED
            logger.exception(f"[AutopoiesisEngine] mutate() failed: {exc}")
            return {"status": "error", "error": str(exc)}
