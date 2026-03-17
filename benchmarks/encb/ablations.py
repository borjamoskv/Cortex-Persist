"""ENCB v2 — Ablation Variants.

Systematically removes components from S3 (Cortex) to measure
each one's contribution. Without ablations, no paper — just propaganda.

Variants:
    S3_no_reliability — r_node fixed at 0.5
    S3_no_atms        — No assumption tracking / nogood invalidation
    S3_no_merge       — LWW instead of CRDT merge (skip merge layer)
    S3_no_freshness   — t_freshness weight = 1.0 always
"""

from __future__ import annotations

from benchmarks.encb.runner import run_single
from benchmarks.encb.metrics import MetricsReport
from benchmarks.encb.strategies import StrategyID


class AblationID:
    """Ablation variant identifiers."""

    NO_RELIABILITY = "S3_no_reliability"
    NO_ATMS = "S3_no_atms"
    NO_MERGE = "S3_no_merge"
    NO_FRESHNESS = "S3_no_freshness"
    FULL = "S3_full"


def run_ablations(
    n_agents: int = 200,
    n_props: int = 1000,
    n_domains: int = 8,
    rounds: int = 30,
    seeds: int = 10,
    corruption_rate: float = 0.20,
) -> dict[str, list[MetricsReport]]:
    """Run all ablation variants across multiple seeds.

    Returns ablation_id → list of MetricsReports (one per seed).
    """
    variants = {
        AblationID.FULL: {
            "use_reliability": True,
            "use_atms": True,
            "use_freshness": True,
        },
        AblationID.NO_RELIABILITY: {
            "use_reliability": False,
            "use_atms": True,
            "use_freshness": True,
        },
        AblationID.NO_ATMS: {
            "use_reliability": True,
            "use_atms": False,
            "use_freshness": True,
        },
        AblationID.NO_FRESHNESS: {
            "use_reliability": True,
            "use_atms": True,
            "use_freshness": False,
        },
    }

    results: dict[str, list[MetricsReport]] = {}

    for ablation_id, flags in variants.items():
        reports: list[MetricsReport] = []
        for s in range(seeds):
            report = run_single(
                strategy=StrategyID.CORTEX,
                n_agents=n_agents,
                n_props=n_props,
                n_domains=n_domains,
                rounds=rounds,
                seed=s,
                corruption_rate=corruption_rate,
                **flags,
            )
            # Override strategy name for grouping
            report.strategy = ablation_id
            reports.append(report)
        results[ablation_id] = reports

    return results


def print_ablation_summary(
    results: dict[str, list[MetricsReport]],
) -> None:
    """Print ablation comparison table."""
    header = f"{'Ablation':<25} {'PFBR':>8} {'EDI':>12} {'CNCL':>8}"
    print("\n" + "=" * 55)
    print("ENCB v2 — Ablation Study")
    print("=" * 55)
    print(header)
    print("-" * 55)

    for ablation_id, reports in results.items():
        avg_pfbr = sum(r.pfbr_final for r in reports) / len(reports)
        avg_edi = sum(r.edi_total for r in reports) / len(reports)
        cncls = [r.cncl_avg for r in reports if r.cncl_avg is not None]
        avg_cncl = sum(cncls) / len(cncls) if cncls else float("inf")
        cncl_str = f"{avg_cncl:.1f}" if avg_cncl != float("inf") else "never"

        print(f"{ablation_id:<25} {avg_pfbr:>8.4f} {avg_edi:>12.1f} {cncl_str:>8}")

    print("=" * 55 + "\n")
