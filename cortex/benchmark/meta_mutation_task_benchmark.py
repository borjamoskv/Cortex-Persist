# Benchmark: META_MUTATION vs. static genome on an external task
"""
This script evaluates whether the adaptive META_MUTATION operator yields a measurable
advantage on a *task‑level* fitness function, not merely on the internal sum of
mutation rates.

It runs two evolutionary streams:
  * **Adaptive** – full mutator (including META_MUTATION).
  * **Static**   – the genome is frozen after the initial creation; no further
    mutations are applied.
"""

import argparse
import copy
import math
import random
import statistics

# Engine imports – these are part of the CORTEX-Persist codebase
from cortex.engine.evo._genome_mutator import GenomeMutator
from cortex.engine.evo._genome_types import MutationType, StrategyGenome
from cortex.isa.builder import dispatch, noop, seq

# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------


def create_random_genome() -> StrategyGenome:
    """Create a synthetic genome with random mutation rates and a simple tree.

    The dispatch tree consists of a sequence of two arithmetic operations that
    operate on the input `x`.  This keeps the evaluation lightweight while still
    allowing the mutator to modify the structure.
    """
    genome = StrategyGenome()
    # Initialise mutation rates uniformly in a modest range
    total = 0.0
    for mt in MutationType:
        rate = random.uniform(0.02, 0.15)
        genome.mutation_rates[mt] = rate
        total += rate
    # Normalise to respect the global budget (0.7)
    if total > 0.7:
        scale = 0.7 / total
        for mt in genome.mutation_rates:
            genome.mutation_rates[mt] *= scale
    # Simple arithmetic tree: (x * a) + b
    a = random.randint(1, 5)
    b = random.randint(0, 10)
    genome.dispatch_tree = seq(
        dispatch("mul", {"factor": a}),
        dispatch("add", {"offset": b}),
    )
    genome.parameters = {}
    genome.lineage.generation = 0
    genome.lineage.mutation_log = []
    return genome


def evaluate_tree(tree, x: int) -> int:
    """Very light interpreter for the toy arithmetic tree.

    Supported nodes:
      - ``dispatch`` with name ``mul`` (expects ``factor``) → returns ``x * factor``
      - ``dispatch`` with name ``add`` (expects ``offset``) → returns ``x + offset``
      - ``seq`` (list of children)               → apply sequentially
      - ``noop``                                   → identity
    """
    if tree == noop():
        return x
    if isinstance(tree, dict):
        # ``seq`` is represented as {"Seq": [child1, child2, ...]}
        if "Seq" in tree:
            result = x
            for child in tree["Seq"]:
                result = evaluate_tree(child, result)
            return result
        # Single dispatch nodes are stored as {"Dispatch": {"target": ..., "payload": ...}}
        if "Dispatch" in tree:
            name = tree["Dispatch"]["target"]
            params = tree["Dispatch"]["payload"]
            if name == "mul":
                return x * params.get("factor", 1)
            if name == "add":
                return x + params.get("offset", 0)
            # Unknown dispatch – treat as identity
            return x
    # Fallback – identity
    return x


def task_fitness(genome: StrategyGenome, inputs: list[int]) -> float:
    """Compute the average negative absolute error against the target function.

    Target: f(x) = 3*x + 7
    Fitness = -mean(|pred - f(x)|)
    Higher (less negative) values are better.
    """
    errors = []
    for x in inputs:
        pred = evaluate_tree(genome.dispatch_tree, x)
        target = 3 * x + 7
        errors.append(abs(pred - target))
    return -statistics.mean(errors)


def diversity_entropy(rates: dict[MutationType, float]) -> float:
    """Normalized Shannon entropy of the mutation‑rate distribution.

    p_i = r_i / Σ r_j   (probability mass)
    H = - Σ p_i log(p_i)
    Normalized by log(N) where N = number of mutation types.
    """
    total = sum(rates.values())
    if total == 0:
        return 0.0
    probs = [r / total for r in rates.values()]
    H = -sum(p * math.log(p) for p in probs if p > 0)
    N = len(rates)
    return H / math.log(N) if N > 1 else 0.0


# ---------------------------------------------------------------------
# Experimental streams
# ---------------------------------------------------------------------


def run_adaptive(
    mutator: GenomeMutator, genome: StrategyGenome, generations: int, inputs: list[int]
) -> tuple[list[float], list[int], list[float]]:
    """Run a stream where the genome is mutated each generation.

    Returns a tuple of:
      1. task‑fitness values per generation
      2. count of META_MUTATION events per generation (0 or 1)
      3. absolute rate drift (max change in any mutation rate) per generation
    """
    fitness_history: list[float] = []
    meta_counts: list[int] = []
    rate_drifts: list[float] = []
    current_fitness = task_fitness(genome, inputs)
    for _ in range(generations):
        pre_rates = genome.mutation_rates.copy()
        child = mutator.mutate(genome)
        child_fitness = task_fitness(child, inputs)
        if child_fitness >= current_fitness:
            genome = child
            current_fitness = child_fitness
        fitness_history.append(current_fitness)
        latest_log = child.lineage.mutation_log[-1] if child.lineage.mutation_log else ""
        meta_counts.append(
            1 if "type=meta_mutation" in latest_log or latest_log.startswith("META:") else 0
        )
        drift = max(abs(child.mutation_rates[mt] - pre_rates.get(mt, 0.0)) for mt in MutationType)
        rate_drifts.append(drift)
    return fitness_history, meta_counts, rate_drifts


def run_static(genome: StrategyGenome, generations: int, inputs: list[int]) -> list[float]:
    """Run a truly static control – the genome never changes.

    Returns a list of repeated task‑fitness values (identical each generation).
    """
    fitness_val = task_fitness(genome, inputs)
    return [fitness_val for _ in range(generations)]


# ---------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="META_MUTATION task‑level benchmark")
    parser.add_argument(
        "-g", "--generations", type=int, default=2000, help="Number of generations per stream"
    )
    parser.add_argument(
        "-r",
        "--repeats",
        type=int,
        default=50,
        help="Number of independent random seeds (experiment repeats)",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=42,
        help="Base seed for reproducibility (each repeat adds its index)",
    )
    args = parser.parse_args()

    mutator = GenomeMutator()
    inputs = list(range(1, 21))  # x = 1..20

    adaptive_means: list[float] = []
    static_means: list[float] = []
    adaptive_diversities: list[float] = []
    static_diversities: list[float] = []
    meta_event_counts: list[int] = []
    rate_drift_means: list[float] = []

    for i in range(args.repeats):
        random.seed(args.seed + i)
        base_genome = create_random_genome()
        adaptive_fitness, meta_counts, drifts = run_adaptive(
            mutator, copy.deepcopy(base_genome), args.generations, inputs
        )
        adaptive_means.append(statistics.mean(adaptive_fitness))
        adaptive_diversities.append(diversity_entropy(base_genome.mutation_rates))
        meta_event_counts.append(sum(meta_counts))
        rate_drift_means.append(statistics.mean(drifts))
        static_fitness = run_static(copy.deepcopy(base_genome), args.generations, inputs)
        static_means.append(statistics.mean(static_fitness))
        static_diversities.append(diversity_entropy(base_genome.mutation_rates))

    def summarize(values: list[float]) -> tuple[float, float]:
        return statistics.mean(values), statistics.stdev(values)

    ad_mean, ad_std = summarize(adaptive_means)
    st_mean, st_std = summarize(static_means)
    delta_mean = ad_mean - st_mean
    pooled_sd = math.sqrt(((ad_std**2) + (st_std**2)) / 2)
    cohen_d = delta_mean / pooled_sd if pooled_sd != 0 else float("inf")
    avg_meta_events = statistics.mean(meta_event_counts) if meta_event_counts else 0.0
    avg_rate_drift = statistics.mean(rate_drift_means) if rate_drift_means else 0.0

    print("\n=== META_MUTATION TASK‑LEVEL BENCHMARK ===")
    print(f"Generations per stream : {args.generations}")
    print(f"Repeats (seeds)       : {args.repeats}\n")
    print("Adaptive stream (META_MUTATION ON):")
    print(f"  Mean task fitness    : {ad_mean:.4f} ± {ad_std:.4f}")
    print("Static stream (no mutation after init):")
    print(f"  Mean task fitness    : {st_mean:.4f} ± {st_std:.4f}\n")
    print("Differences:")
    print(f"  Δ mean fitness       : {delta_mean:.4f}")
    print(f"  Cohen's d (effect size) : {cohen_d:.3f}\n")
    print("Diversity (Shannon entropy) – diagnostic only:")
    print(f"  Adaptive avg entropy : {statistics.mean(adaptive_diversities):.3f}")
    print(f"  Static   avg entropy : {statistics.mean(static_diversities):.3f}\n")
    print("META_MUTATION instrumentation:")
    print(f"  Total META events across all repeats : {sum(meta_event_counts)}")
    print(f"  Avg META events per repeat          : {avg_meta_events:.2f}")
    print(f"  Avg absolute rate drift per generation: {avg_rate_drift:.5f}\n")

    try:
        import csv

        csv_path = "meta_mutation_task_results.csv"
        with open(csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "repeat",
                    "adaptive_fitness",
                    "static_fitness",
                    "adaptive_entropy",
                    "static_entropy",
                    "meta_events",
                    "avg_rate_drift",
                ]
            )
            for idx in range(args.repeats):
                writer.writerow(
                    [
                        idx,
                        adaptive_means[idx],
                        static_means[idx],
                        adaptive_diversities[idx],
                        static_diversities[idx],
                        meta_event_counts[idx],
                        rate_drift_means[idx],
                    ]
                )
        print(f"Results written to {csv_path}")
    except Exception as e:
        print(f"CSV export failed: {e}")


if __name__ == "__main__":
    main()
