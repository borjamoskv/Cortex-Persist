"""E1 Profiler — offline thermodynamic observability for Cortex traces.

Usage (CLI):

    python -m cortex.tools.e1_profiler traces.jsonl
    python -m cortex.tools.e1_profiler traces.jsonl --weights alpha=1.0 beta=2.0

Usage (library):

    from legacy_research.tools.e1_profiler import E1Profiler
    from legacy_research.tools.trace_adapter import ExecutionTrace

    profiler = E1Profiler()
    report = profiler.profile(traces)
    print(report.summary())

This module is intentionally self-contained. It reads ExecutionTrace
objects, runs MetaArbiterKernel.score() on each one, and aggregates
statistics into a ProfileReport.

It does NOT touch the live engine, ledger, or database.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from cortex.engine.meta_arbiter import MetaArbiterKernel, TrajectoryScore
from legacy_research.tools.trace_adapter import ExecutionTrace
from legacy_research.tools.trace_builder import TraceBuilder

# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------


@dataclass
class ComponentStats:
    """Descriptive statistics for a single E1 component."""

    mean: float
    variance: float
    minimum: float
    maximum: float

    @classmethod
    def from_values(cls, values: list[float]) -> ComponentStats:
        if not values:
            return cls(mean=0.0, variance=0.0, minimum=0.0, maximum=0.0)
        return cls(
            mean=statistics.mean(values),
            variance=statistics.variance(values) if len(values) > 1 else 0.0,
            minimum=min(values),
            maximum=max(values),
        )


@dataclass
class ProfileReport:
    """Aggregated E1 profile over a corpus of traces.

    Fields
    ------
    n_traces:         Number of traces analyzed.
    energy:           Stats for the full E1 scalar.
    D_ledger:         Stats for the ledger inconsistency component.
    D_causal:         Stats for the causal violation component.
    D_consensus:      Stats for the consensus conflict component.
    H_branch:         Stats for the branch entropy component.
    D_proj:           Stats for the projection error component.
    positive_dE_rate: Fraction of consecutive pairs where E increased.
    regime:           Inferred system regime.
    """

    n_traces: int
    energy: ComponentStats
    D_ledger: ComponentStats
    D_causal: ComponentStats
    D_consensus: ComponentStats
    H_branch: ComponentStats
    D_proj: ComponentStats
    positive_dE_rate: float
    regime: str  # "stable" | "chaotic_controlled" | "divergent" | "unknown"

    def summary(self) -> str:
        lines = [
            f"E1 Profile — {self.n_traces} traces",
            f"  regime:           {self.regime}",
            f"  energy.mean:      {self.energy.mean:.4f}",
            f"  energy.variance:  {self.energy.variance:.4f}",
            f"  positive_dE_rate: {self.positive_dE_rate:.2%}",
            "",
            "  Components (mean):",
            f"    D_ledger:   {self.D_ledger.mean:.4f}",
            f"    D_causal:   {self.D_causal.mean:.4f}",
            f"    D_consensus:{self.D_consensus.mean:.4f}",
            f"    H_branch:   {self.H_branch.mean:.4f}",
            f"    D_proj:     {self.D_proj.mean:.4f}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class E1Profiler:
    """Offline E1 energy profiler over ExecutionTrace corpora.

    Args
    ----
    alpha, beta, gamma, delta, epsilon:
        Weights for E1 components (D_ledger, D_causal, D_consensus,
        H_branch, D_proj respectively).
    stable_threshold:     Max mean energy to classify as 'stable'.
    chaotic_max_variance: Max variance for 'chaotic_controlled'.
    positive_dE_threshold: Min positive-dE rate to classify as 'divergent'.
    """

    def __init__(
        self,
        *,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
        delta: float = 1.0,
        epsilon: float = 1.0,
        stable_threshold: float = 0.3,
        chaotic_max_variance: float = 0.1,
        positive_dE_threshold: float = 0.4,
    ) -> None:
        self._kernel = MetaArbiterKernel(
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            delta=delta,
            epsilon=epsilon,
        )
        self._stable_threshold = stable_threshold
        self._chaotic_max_variance = chaotic_max_variance
        self._positive_dE_threshold = positive_dE_threshold

    def score_trace(self, trace: ExecutionTrace) -> TrajectoryScore:
        """Score a single trace with no engine wiring (all signals trace-local)."""
        return self._kernel.score(
            trace,
            state=None,
            causal_graph=None,
            vote_ledger=None,
            replay_engine=None,
        )

    def profile(self, traces: Iterable[ExecutionTrace]) -> ProfileReport:
        """Compute an E1 ProfileReport over a corpus of traces."""
        scores: list[TrajectoryScore] = []
        for trace in traces:
            scores.append(self.score_trace(trace))

        n = len(scores)
        if n == 0:
            empty = ComponentStats(mean=0.0, variance=0.0, minimum=0.0, maximum=0.0)
            return ProfileReport(
                n_traces=0,
                energy=empty,
                D_ledger=empty,
                D_causal=empty,
                D_consensus=empty,
                H_branch=empty,
                D_proj=empty,
                positive_dE_rate=0.0,
                regime="unknown",
            )

        energies = [s.energy for s in scores]

        # positive dE rate: fraction of steps where energy increases
        positive_dE = sum(
            1 for a, b in zip(energies, energies[1:], strict=False) if b > a + self._kernel.eps
        )
        positive_dE_rate = positive_dE / max(1, n - 1)

        report = ProfileReport(
            n_traces=n,
            energy=ComponentStats.from_values(energies),
            D_ledger=ComponentStats.from_values([s.D_ledger for s in scores]),
            D_causal=ComponentStats.from_values([s.D_causal for s in scores]),
            D_consensus=ComponentStats.from_values([s.D_consensus for s in scores]),
            H_branch=ComponentStats.from_values([s.H_branch for s in scores]),
            D_proj=ComponentStats.from_values([s.D_proj for s in scores]),
            positive_dE_rate=positive_dE_rate,
            regime=self._classify_regime(
                mean_energy=statistics.mean(energies),
                variance=statistics.variance(energies) if n > 1 else 0.0,
                positive_dE_rate=positive_dE_rate,
            ),
        )
        return report

    def _classify_regime(self, mean_energy: float, variance: float, positive_dE_rate: float) -> str:
        if positive_dE_rate >= self._positive_dE_threshold:
            return "divergent"
        if mean_energy < self._stable_threshold and variance < self._chaotic_max_variance:
            return "stable"
        if variance < self._chaotic_max_variance:
            return "stable"
        return "chaotic_controlled"

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    @staticmethod
    def load_jsonl(path: str | Path) -> list[ExecutionTrace]:
        """Load ExecutionTrace objects from a jsonl file.

        Each line must be a JSON object previously produced by
        `ExecutionTrace.as_dict()` + any events stored separately.
        This loader reconstructs minimal ExecutionTrace objects from
        the fields that `as_dict()` exposes (no events wiring needed
        for offline energy scoring with current trace-local components).
        """
        traces: list[ExecutionTrace] = []
        p = Path(path)
        if not p.exists():
            return traces

        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                builder = TraceBuilder(
                    tenant_id=obj.get("tenant_id"),
                    model_version=obj.get("model_version", "unknown"),
                    op_kind=obj.get("op_kind", "unknown"),
                    trace_id=obj.get("id"),
                )
                # Reconstruct write/read/mutation events from counters
                for _ in range(obj.get("writes", 0)):
                    builder.record("write")
                for _ in range(obj.get("reads", 0)):
                    builder.record("read")
                for _ in range(obj.get("mutations", 0)):
                    builder.record("mutation")
                traces.append(builder.build())

        return traces


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _parse_weights(args: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for item in args:
        if "=" in item:
            k, v = item.split("=", 1)
            weights[k.strip()] = float(v.strip())
    return weights


def main(argv: list[str] | None = None) -> None:
    import sys

    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("Usage: python -m cortex.tools.e1_profiler <traces.jsonl> [key=value ...]")
        sys.exit(1)

    path = args[0]
    weight_args = args[1:]
    weights = _parse_weights(weight_args)

    profiler = E1Profiler(
        alpha=weights.get("alpha", 1.0),
        beta=weights.get("beta", 1.0),
        gamma=weights.get("gamma", 1.0),
        delta=weights.get("delta", 1.0),
        epsilon=weights.get("epsilon", 1.0),
    )

    traces = E1Profiler.load_jsonl(path)
    if not traces:
        print(f"No traces loaded from {path}")
        sys.exit(1)

    report = profiler.profile(traces)
    print(report.summary())


if __name__ == "__main__":
    main()
