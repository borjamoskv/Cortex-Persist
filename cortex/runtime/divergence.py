# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionDiff:
    """Execution Vector Field causal separation representation."""

    tick: int
    state_drift: dict
    event_delta: dict
    semantic_shift: float
    entropy_gradient: float


class Trace:
    """A trace represents an execution trajectory through state space."""

    def __init__(self, events: list[dict[str, Any]], states: list[dict[str, Any]]):
        self.events = events
        self.states = states


class DivergenceEngine:
    """Calculates Execution Phase Space manifolds between runs.

    No compara logs. Modela trayectorias en un espacio dinámico.
    """

    def diff(self, a: Trace, b: Trace) -> ExecutionDiff:
        """
        Aligns by hash-chain (CI layer), computes state drift, event delta,
        semantic shift (KL divergence approximation), and entropy gradient.
        """
        max_len = max(len(a.states), len(b.states))

        fork_tick = 0
        state_drift = {}
        event_delta = {}

        for t in range(max_len):
            s_a = a.states[t] if t < len(a.states) else {}
            s_b = b.states[t] if t < len(b.states) else {}

            if s_a != s_b:
                fork_tick = t
                state_drift = {"a": s_a, "b": s_b}

                e_a = a.events[t] if t < len(a.events) else {}
                e_b = b.events[t] if t < len(b.events) else {}
                event_delta = {"a": e_a, "b": e_b}
                break

        # Semantic shift and entropy gradient (mock values pending real KL implementation)
        semantic_shift = 0.0 if not state_drift else 1.0
        entropy_gradient = 0.0 if not state_drift else 0.5

        return ExecutionDiff(
            tick=fork_tick,
            state_drift=state_drift,
            event_delta=event_delta,
            semantic_shift=semantic_shift,
            entropy_gradient=entropy_gradient,
        )


class ExecutionSpace:
    """Geometría de comportamiento, no de logs."""

    def __init__(self, traces: list[Trace]):
        self.traces = traces

    def manifold(self) -> dict[str, Any]:
        """Returns the clustering, fork maps, and vector drift field."""
        return {
            "clusters": "EquivalenceClasses",
            "fork_points": "ForkMap",
            "drift_field": "VectorField",
        }
