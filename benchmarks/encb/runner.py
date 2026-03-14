"""ENCB v2 — Monte Carlo Simulation Runner.

Orchestrates the full benchmark: universe generation, agent population,
multi-round observation/resolution, metrics collection, and JSON export.

Usage:
    python -m benchmarks.encb.runner --n-agents 200 --n-props 1000 --rounds 30 --seeds 10
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmarks.encb.agents import (
    AdversaryType,
    NodeProfile,
    create_agent_population,
    generate_observation_boolean,
    generate_observation_categorical,
    generate_observation_scalar,
    generate_observation_set,
)
from benchmarks.encb.atms import ATMSLite
from benchmarks.encb.belief_object import BeliefType
from benchmarks.encb.metrics import MetricsReport, compute_report
from benchmarks.encb.strategies import (
    Observation,
    PropState,
    StrategyID,
    resolve_cortex,
    resolve_crdt_only,
    resolve_lww,
    resolve_rag,
)
from benchmarks.encb.universe import Proposition, Universe, generate_universe


def _generate_observations(
    prop: Proposition,
    nodes: list[NodeProfile],
    clique_lies: dict[str, Any],
) -> list[Observation]:
    """Generate one observation per node for a proposition."""
    obs: list[Observation] = []

    for node in nodes:
        clique_lie = clique_lies.get(prop.key) if node.clique_id else None

        if prop.belief_type == BeliefType.BOOLEAN:
            val, conf = generate_observation_boolean(
                prop.ground_truth, node, clique_lie
            )
        elif prop.belief_type == BeliefType.CATEGORICAL:
            val, conf = generate_observation_categorical(
                prop.ground_truth, prop.categories, node, clique_lie
            )
        elif prop.belief_type == BeliefType.SCALAR:
            val, conf = generate_observation_scalar(
                prop.ground_truth, node
            )
        elif prop.belief_type == BeliefType.SET:
            val, conf = generate_observation_set(
                prop.ground_truth, node, prop.set_universe or None
            )
        else:
            val, conf = prop.ground_truth, 0.5

        obs.append((node, val, conf))

    return obs


def _pre_generate_clique_lies(
    universe: Universe,
    nodes: list[NodeProfile],
) -> dict[str, Any]:
    """Pre-generate coordinated lies for clique nodes."""
    clique_lies: dict[str, Any] = {}
    has_clique = any(
        n.adversary_type == AdversaryType.COORDINATED_CLIQUE for n in nodes
    )
    if not has_clique:
        return clique_lies

    for key, prop in universe.propositions.items():
        if prop.belief_type == BeliefType.BOOLEAN:
            clique_lies[key] = not prop.ground_truth
        elif prop.belief_type == BeliefType.CATEGORICAL:
            wrong = [c for c in prop.categories if c != prop.ground_truth]
            clique_lies[key] = random.choice(wrong) if wrong else prop.ground_truth
        elif prop.belief_type == BeliefType.SCALAR:
            clique_lies[key] = prop.ground_truth * random.uniform(2.0, 5.0)
        elif prop.belief_type == BeliefType.SET:
            extras = (prop.set_universe or set()) - prop.ground_truth
            clique_lies[key] = extras if extras else prop.ground_truth

    return clique_lies


def run_single(
    strategy: StrategyID,
    n_agents: int = 200,
    n_props: int = 1000,
    n_domains: int = 8,
    rounds: int = 30,
    corruption_rate: float = 0.20,
    hallucinator_rate: float = 0.05,
    clique_size: int = 10,
    stale_rate: float = 0.05,
    drift_rate: float = 0.03,
    seed: int = 42,
    # Ablation flags (only for S3)
    use_reliability: bool = True,
    use_atms: bool = True,
    use_freshness: bool = True,
) -> MetricsReport:
    """Run a single simulation for one strategy and one seed.

    Returns a MetricsReport with all 4 formal metrics.
    """
    random.seed(seed)

    # Generate universe and agents
    universe = generate_universe(n_props, n_domains, seed=seed)
    nodes = create_agent_population(
        n_agents,
        corruption_rate=corruption_rate,
        hallucinator_rate=hallucinator_rate,
        clique_size=clique_size,
        stale_rate=stale_rate,
        drift_rate=drift_rate,
    )

    # Initialize prop states
    states: dict[str, PropState] = {}
    for key, prop in universe.propositions.items():
        states[key] = PropState(
            key=key,
            belief_type=prop.belief_type,
            truth=prop.ground_truth,
            categories=prop.categories,
            set_universe=prop.set_universe,
        )

    # Pre-generate clique lies
    clique_lies = _pre_generate_clique_lies(universe, nodes)

    # ATMS for S3
    atms = ATMSLite() if strategy == StrategyID.CORTEX else None

    # Track snapshots and reliability history
    round_snapshots: list[list[PropState]] = []
    reliability_history: dict[str, list[float]] = defaultdict(list)

    # ── Main simulation loop ──────────────────────────────────────────────
    for t in range(rounds):
        for key, prop in universe.propositions.items():
            state = states[key]

            # Generate observations
            obs = _generate_observations(prop, nodes, clique_lies)

            # Resolve based on strategy
            if strategy == StrategyID.LWW:
                resolve_lww(state, obs, t)
            elif strategy == StrategyID.RAG:
                resolve_rag(state, obs, t)
            elif strategy == StrategyID.CRDT_ONLY:
                resolve_crdt_only(state, obs, t)
            elif strategy == StrategyID.CORTEX:
                resolve_cortex(
                    state, obs, t,
                    atms=atms,
                    use_reliability=use_reliability,
                    use_atms=use_atms,
                    use_freshness=use_freshness,
                )

        # Snapshot for metrics
        snapshot = []
        for s in states.values():
            snap = PropState(
                key=s.key,
                belief_type=s.belief_type,
                truth=s.truth,
                categories=s.categories,
                set_universe=s.set_universe,
            )
            snap.current_value = s.current_value
            snap.confidence = s.confidence
            snap.conflict_mass = s.conflict_mass
            snapshot.append(snap)
        round_snapshots.append(snapshot)

        # Track reliability
        for node in nodes:
            reliability_history[node.node_id].append(node.reliability)

    # Compute report
    final_states = list(states.values())
    return compute_report(
        strategy=strategy.value,
        seed=seed,
        final_states=final_states,
        round_snapshots=round_snapshots,
        reliability_history=dict(reliability_history),
        nodes=nodes,
    )


def run_benchmark(
    n_agents: int = 200,
    n_props: int = 1000,
    n_domains: int = 8,
    rounds: int = 30,
    seeds: int = 10,
    corruption_rate: float = 0.20,
    strategies: list[StrategyID] | None = None,
) -> dict[str, list[MetricsReport]]:
    """Run the full benchmark across all strategies and seeds.

    Returns strategy_id → list of MetricsReports (one per seed).
    """
    if strategies is None:
        strategies = list(StrategyID)

    results: dict[str, list[MetricsReport]] = {}

    for strat in strategies:
        reports: list[MetricsReport] = []
        for s in range(seeds):
            report = run_single(
                strategy=strat,
                n_agents=n_agents,
                n_props=n_props,
                n_domains=n_domains,
                rounds=rounds,
                seed=s,
                corruption_rate=corruption_rate,
            )
            reports.append(report)
        results[strat.value] = reports

    return results


def export_results(
    results: dict[str, list[MetricsReport]],
    output_path: str,
) -> None:
    """Export results to JSON."""
    data: dict[str, Any] = {}
    for strat, reports in results.items():
        data[strat] = [
            {
                "strategy": r.strategy,
                "seed": r.seed,
                "pfbr_final": r.pfbr_final,
                "ter_round": r.ter_round,
                "edi_total": r.edi_total,
                "cncl_avg": r.cncl_avg,
                "avg_conflict_mass": r.avg_conflict_mass,
                "avg_reliability": r.avg_reliability,
                "error_rate_by_type": r.error_rate_by_type,
            }
            for r in reports
        ]

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def print_summary(results: dict[str, list[MetricsReport]]) -> None:
    """Print a summary table to stdout."""
    header = f"{'Strategy':<20} {'PFBR':>8} {'TER':>8} {'EDI':>12} {'CNCL':>8}"
    print("\n" + "=" * 60)
    print("ENCB v2 — Benchmark Results")
    print("=" * 60)
    print(header)
    print("-" * 60)

    for strat, reports in results.items():
        avg_pfbr = sum(r.pfbr_final for r in reports) / len(reports)
        ters = [r.ter_round for r in reports if r.ter_round is not None]
        avg_ter = sum(ters) / len(ters) if ters else float("inf")
        avg_edi = sum(r.edi_total for r in reports) / len(reports)
        cncls = [r.cncl_avg for r in reports if r.cncl_avg is not None]
        avg_cncl = sum(cncls) / len(cncls) if cncls else float("inf")

        ter_str = f"{avg_ter:.1f}" if avg_ter != float("inf") else "never"
        cncl_str = f"{avg_cncl:.1f}" if avg_cncl != float("inf") else "never"

        print(f"{strat:<20} {avg_pfbr:>8.4f} {ter_str:>8} {avg_edi:>12.1f} {cncl_str:>8}")

    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ENCB v2 — Epistemic Noise Chaos Benchmark"
    )
    parser.add_argument("--n-agents", type=int, default=200)
    parser.add_argument("--n-props", type=int, default=1000)
    parser.add_argument("--n-domains", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--corruption", type=float, default=0.20)
    parser.add_argument("--export", type=str, default=None)
    args = parser.parse_args()

    t0 = time.perf_counter()

    results = run_benchmark(
        n_agents=args.n_agents,
        n_props=args.n_props,
        n_domains=args.n_domains,
        rounds=args.rounds,
        seeds=args.seeds,
        corruption_rate=args.corruption,
    )

    elapsed = time.perf_counter() - t0

    print_summary(results)
    print(f"Elapsed: {elapsed:.1f}s")

    if args.export:
        export_results(results, args.export)
        print(f"Results exported to {args.export}")


if __name__ == "__main__":
    main()
