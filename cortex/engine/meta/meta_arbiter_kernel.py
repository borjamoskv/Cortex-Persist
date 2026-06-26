# [C5-REAL] Exergy-Maximized
"""CORTEX Meta-Arbiter Kernel — Thermodynamic Trace Collapse.

Provides the thermodynamic collapse operator over ExecutionTrace objects,
as specified in the E1 profiler blueprint.

Reality Level: C5-REAL
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cortex.tools.trace_adapter import ExecutionTrace


@dataclass(frozen=True)
class TrajectoryScore:
    """Energy breakdown for a single trajectory.

    All components are normalized to [0, 1] where possible.
    The overall `energy` is a weighted sum of the components.
    """

    energy: float
    D_ledger: float
    D_causal: float
    D_consensus: float
    H_branch: float
    D_proj: float
    valid: bool


@dataclass(frozen=True)
class CollapseReceipt:
    """Structured receipt for a collapse decision.

    winning_id: id of the chosen trajectory (or "" if none).
    scores: mapping from trajectory id -> TrajectoryScore.
    state_snapshot: lightweight snapshot of the state associated
                    with this collapse operation.
    eps: numerical tolerance used during selection.
    """

    winning_id: str
    scores: dict[str, TrajectoryScore]
    state_snapshot: Any
    eps: float


class MetaArbiterKernel:
    """Thermodynamic collapse operator over ExecutionTrace.

    This class does not reach into the engine internals directly.
    Instead, it operates over ExecutionTrace objects and opaque
    `state` / `causal_graph` / `vote_ledger` / `replay_engine`
    placeholders, so that callers can progressively wire real
    integrations without breaking the core contract.

    The initial implementation keeps all components trace-local:

    - D_ledger, D_causal, D_consensus, D_proj are 0.0 by default
      (placeholders to be wired to real signals later).
    - H_branch is a simple monotonic function of trace length, acting
      as a proxy for branching/complexity. This makes the operator
      usable in tests and basic profiling without requiring full
      engine wiring.
    """

    def __init__(
        self,
        *,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
        delta: float = 1.0,
        epsilon: float = 1.0,
        eps: float = 1e-6,
    ) -> None:
        # We keep weights explicit for future tuning.
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.delta = float(delta)
        self.epsilon = float(epsilon)
        self.eps = float(eps)

    # ------------------------------------------------------------------
    # Component helpers (trace-local fallbacks)
    # ------------------------------------------------------------------

    def _D_ledger(self, trace: ExecutionTrace, state: Any) -> float:
        """Ledger vs trace inconsistency.

        Placeholder for now: returns 0.0.
        A future version can compare `trace.persisted_events()` with
        the ledger snapshot in `state`.
        """
        return 0.0

    def _D_causal(self, trace: ExecutionTrace, causal_graph: Any) -> float:
        """Causal violation rate.

        Placeholder for now: returns 0.0.
        A future version can query the causal graph for invalid
        edges implied by the trace.
        """
        return 0.0

    def _D_consensus(self, trace: ExecutionTrace, vote_ledger: Any) -> float:
        """Consensus conflict score.

        Placeholder for now: returns 0.0.
        A future version can aggregate disagreement between this
        trajectory and the vote ledger.
        """
        return 0.0

    def _H_branch(self, trace: ExecutionTrace, state: Any) -> float:
        """Branch entropy proxy based on trace length.

        This is *not* the true branching entropy over future
        trajectories, but a monotonic proxy that:
        - is 0.0 for empty traces,
        - grows with the number of events,
        - saturates at 1.0 around 100 events.
        """
        length = trace.length()
        if length <= 0:
            return 0.0
        return min(1.0, length / 100.0)

    def _D_proj(self, trace: ExecutionTrace, state: Any, replay_engine: Any) -> float:
        """Projection error between replayed and actual state.

        Placeholder: returns 0.0 until a stable replay/state-distance
        API is wired in. The signature is kept to match the E1
        specification so callers can start threading a replay_engine
        through the call stack without breaking this module.
        """
        return 0.0

    def _snapshot_state(self, state: Any) -> Any:
        """Lightweight state snapshot for receipts.

        Heuristic:
        - prefer `state.id` if present,
        - else `state.height`,
        - else `hash(state)` or `repr(state)`.
        """
        if hasattr(state, "id"):
            return state.id
        if hasattr(state, "height"):
            return state.height
        try:
            return hash(state)
        except Exception:
            return repr(state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        trace: ExecutionTrace,
        *,
        state: Any,
        causal_graph: Any,
        vote_ledger: Any,
        replay_engine: Any,
    ) -> TrajectoryScore:
        """Compute the E1-style energy and its components for a trace.

        All arguments other than `trace` are kept opaque here to
        avoid coupling this module to specific engine internals.
        """
        d_ledger = self._D_ledger(trace, state)
        d_causal = self._D_causal(trace, causal_graph)
        d_consensus = self._D_consensus(trace, vote_ledger)
        h_branch = self._H_branch(trace, state)
        d_proj = self._D_proj(trace, state, replay_engine)

        energy = (
            self.alpha * d_ledger
            + self.beta * d_causal
            + self.gamma * d_consensus
            + self.delta * h_branch
            + self.epsilon * d_proj
        )

        return TrajectoryScore(
            energy=energy,
            D_ledger=d_ledger,
            D_causal=d_causal,
            D_consensus=d_consensus,
            H_branch=h_branch,
            D_proj=d_proj,
            valid=True,
        )

    def collapse(
        self,
        futures: Iterable[ExecutionTrace],
        *,
        state: Any,
        causal_graph: Any,
        vote_ledger: Any,
        replay_engine: Any,
    ) -> tuple[ExecutionTrace | None, CollapseReceipt]:
        """Collapse a set of candidate trajectories into a single winner.

        Returns the chosen ExecutionTrace (or None if the set is
        empty) and a CollapseReceipt containing the full score
        breakdown for all candidates.
        """
        scores: dict[str, TrajectoryScore] = {}
        candidates: list[ExecutionTrace] = []

        for trace in futures:
            sc = self.score(
                trace,
                state=state,
                causal_graph=causal_graph,
                vote_ledger=vote_ledger,
                replay_engine=replay_engine,
            )
            scores[trace.id] = sc
            if sc.valid:
                candidates.append(trace)

        if not candidates:
            receipt = CollapseReceipt(
                winning_id="",
                scores=scores,
                state_snapshot=self._snapshot_state(state),
                eps=self.eps,
            )
            return None, receipt

        winner = min(candidates, key=lambda t: scores[t.id].energy)
        receipt = CollapseReceipt(
            winning_id=winner.id,
            scores=scores,
            state_snapshot=self._snapshot_state(state),
            eps=self.eps,
        )
        return winner, receipt
