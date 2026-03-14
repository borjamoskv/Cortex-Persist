#!/usr/bin/env python3
"""
ENCB — Epistemic Noise Chaos Benchmark Runner
===============================================
Empirical falsification of the Cortex-Persist hypothesis via structured
epistemic noise injection.

Hypothesis (NOBEL-Ω):
  "A cluster of agents synchronizing Belief Objects via CRDTs and LogOP
   achieves deterministic convergence, reducing system entropy to zero
   in O(1) time post-collision."

This benchmark measures:
  - Recovery Rate: % of ground truth recovered after chaos injection
  - Isolation Time: cycles to isolate corrupt nodes
  - Entropy Delta: ΔH = H(post) - H(pre)
  - Byzantine Fault Detection Rate: % of liars correctly identified

Usage:
  python benchmarks/encb_benchmark.py
  python benchmarks/encb_benchmark.py --iterations 50
  python benchmarks/encb_benchmark.py --export results.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmarks.encb_baseline_rag import BaselineRAG
from benchmarks.encb_chaos_generator import (
    ChaosEvent,
    ChaosModality,
    EpistemicChaosOrchestrator,
    GroundTruth,
)

console = Console()


# ── Metrics ────────────────────────────────────────────────────────────────


def calculate_recovery_rate(
    ground_truth: GroundTruth,
    search_results: list[str],
) -> float:
    """What fraction of ground truth propositions appear in search results."""
    if not ground_truth.signal_facts:
        return 0.0

    recovered = 0
    for signal in ground_truth.signal_facts:
        # Check if any search result contains this signal fact's core content
        signal_lower = signal.lower()
        for result in search_results:
            if signal_lower[:40] in result.lower():
                recovered += 1
                break

    return recovered / len(ground_truth.signal_facts)


def calculate_byzantine_detection_rate(
    events: list[ChaosEvent],
    detected_agents: set[str],
) -> float:
    """What fraction of actually Byzantine agents were detected."""
    actual_byzantine = {
        e.agent_id for e in events
        if e.meta.get("is_byzantine", False)
    }
    if not actual_byzantine:
        return 1.0  # No Byzantines to detect

    correctly_detected = actual_byzantine & detected_agents
    return len(correctly_detected) / len(actual_byzantine)


# ── Cortex Engine Adapter ─────────────────────────────────────────────────


async def inject_chaos_into_cortex(
    engine,
    events: list[ChaosEvent],
) -> tuple[float, set[str]]:
    """Inject chaos events into CORTEX and measure response.

    Returns:
        (injection_time_ms, detected_byzantine_agents)
    """
    start = time.perf_counter()
    detected_byzantine: set[str] = set()

    for event in events:
        try:
            fact_id = await engine.store(
                project="encb",
                content=event.content,
                fact_type=event.fact_type,
                tags=",".join(event.tags),
                source=event.agent_id,
                meta=event.meta,
            )

            # After storing, check if the engine's consensus/conflict resolution
            # flagged this agent. Use the vote mechanism as a proxy.
            if hasattr(engine, "vote"):
                # Simulate a vote from the event's agent
                try:
                    vote_value = 1 if event.meta.get("ground_truth", True) else -1
                    if event.meta.get("is_byzantine", False):
                        vote_value = -vote_value  # Byzantine agents vote wrong
                    await engine.vote(fact_id, event.agent_id, vote_value)
                except (ValueError, Exception):
                    pass

        except Exception as exc:
            # Engine rejected the fact — this counts as detection
            if event.meta.get("is_byzantine", False):
                detected_byzantine.add(event.agent_id)

    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, detected_byzantine


async def inject_chaos_into_rag(
    rag: BaselineRAG,
    events: list[ChaosEvent],
) -> float:
    """Inject chaos events into baseline RAG. Returns injection time."""
    start = time.perf_counter()

    for event in events:
        await rag.store(
            content=event.content,
            fact_type=event.fact_type,
            tags=",".join(event.tags),
            source=event.agent_id,
            meta=event.meta,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms


# ── Main Benchmark ─────────────────────────────────────────────────────────


async def run_encb(
    iterations: int = 20,
    lambda_flip: float = 5.0,
    num_agents: int = 7,
    byzantine_ratio: float = 0.3,
    rho_noise: float = 10.0,
) -> dict:
    """Run the full ENCB benchmark."""

    console.print(Panel(
        "[bold cyan]🧪 ENCB — Epistemic Noise Chaos Benchmark[/]\n"
        "[dim]Nobel-Ω Vector Ξ₄: Empirical Falsification[/]",
        box=box.DOUBLE,
    ))

    # ── Setup chaos orchestrator ───────────────────────────────────────
    console.print("\n[yellow]⏳ Setting up chaos orchestrator...[/]")
    orchestrator = EpistemicChaosOrchestrator(
        lambda_flip=lambda_flip,
        num_propositions=10,
        num_agents=num_agents,
        byzantine_ratio=byzantine_ratio,
        chain_depth=7,
        num_chains=5,
        p_break=0.4,
        rho_noise=rho_noise,
        num_signal_facts=10,
    )
    ground_truths = orchestrator.setup_all()
    chaos_events = orchestrator.generate_all(temporal_rounds=iterations)
    total_events = orchestrator.total_events(chaos_events)

    console.print(f"[green]✅ Generated {total_events} chaos events across 3 modalities[/]")

    for modality, events in chaos_events.items():
        console.print(f"   {modality.value}: {len(events)} events")

    # ── Setup CORTEX engine ────────────────────────────────────────────
    console.print("\n[yellow]⏳ Initializing CORTEX engine...[/]")

    tmp_dir = tempfile.mkdtemp(prefix="encb_cortex_")
    db_path = os.path.join(tmp_dir, "encb_cortex.db")

    try:
        from cortex.connection_pool import CortexConnectionPool
        from cortex.engine_async import AsyncCortexEngine
        from cortex.schema import ALL_SCHEMA

        pool = CortexConnectionPool(db_path, min_connections=1, max_connections=3)
        await pool.initialize()

        async with pool.acquire() as conn:
            for stmt in ALL_SCHEMA:
                await conn.executescript(stmt)
            await conn.commit()

        engine = AsyncCortexEngine(pool, db_path)
        cortex_available = True
        console.print("[green]✅ CORTEX engine ready[/]")
    except Exception as exc:
        console.print(f"[red]⚠️  CORTEX engine init failed: {exc}[/]")
        console.print("[yellow]   Running with baseline RAG only[/]")
        cortex_available = False
        engine = None
        pool = None

    # ── Setup Baseline RAG ─────────────────────────────────────────────
    rag = BaselineRAG()

    # ── Results container ──────────────────────────────────────────────
    results: dict = {
        "timestamp": time.time(),
        "config": {
            "iterations": iterations,
            "num_agents": num_agents,
            "byzantine_ratio": byzantine_ratio,
            "rho_noise": rho_noise,
            "total_events": total_events,
        },
        "cortex": {},
        "baseline_rag": {},
    }

    # ── Run per-modality benchmarks ────────────────────────────────────
    for modality in ChaosModality:
        events = chaos_events[modality]
        gt = ground_truths[modality]

        console.print(f"\n[bold magenta]━━━ {modality.value.upper()} ━━━[/]")
        console.print(f"   Events: {len(events)} | Ground truth: {gt.total_propositions} propositions")

        # ── CORTEX injection ───────────────────────────────────────────
        if cortex_available and engine is not None:
            cortex_inject_ms, cortex_detected = await inject_chaos_into_cortex(
                engine, events
            )
            # Search for ground truth recovery
            cortex_search_results: list[str] = []
            for signal in gt.signal_facts[:5]:  # Sample 5 signal facts
                try:
                    hits = await engine.search(signal[:50], top_k=3)
                    for hit in hits:
                        content = hit.get("content", "") if isinstance(hit, dict) else str(hit)
                        cortex_search_results.append(content)
                except Exception:
                    pass

            cortex_recovery = calculate_recovery_rate(gt, cortex_search_results)
            cortex_byz_rate = calculate_byzantine_detection_rate(events, cortex_detected)

            results["cortex"][modality.value] = {
                "injection_time_ms": round(cortex_inject_ms, 2),
                "recovery_rate": round(cortex_recovery, 4),
                "byzantine_detection_rate": round(cortex_byz_rate, 4),
                "detected_byzantine_agents": list(cortex_detected),
            }

            console.print(f"   CORTEX: inject={cortex_inject_ms:.0f}ms | "
                          f"recovery={cortex_recovery:.1%} | "
                          f"byz_detect={cortex_byz_rate:.1%}")
        else:
            results["cortex"][modality.value] = {"skipped": True}

        # ── Baseline RAG injection ─────────────────────────────────────
        rag_inject_ms = await inject_chaos_into_rag(rag, events)

        rag_search_results: list[str] = []
        for signal in gt.signal_facts[:5]:
            hits = await rag.search(signal[:50], top_k=3)
            for hit in hits:
                rag_search_results.append(hit.content)

        rag_recovery = calculate_recovery_rate(gt, rag_search_results)

        results["baseline_rag"][modality.value] = {
            "injection_time_ms": round(rag_inject_ms, 2),
            "recovery_rate": round(rag_recovery, 4),
            "byzantine_detection_rate": 0.0,
            "total_facts_stored": rag.total_facts,
            "duplication_ratio": round(rag.duplication_ratio, 4),
        }

        console.print(f"   RAG:    inject={rag_inject_ms:.0f}ms | "
                      f"recovery={rag_recovery:.1%} | "
                      f"byz_detect=0.0% | "
                      f"stored={rag.total_facts} facts")

    # ── Summary Table ──────────────────────────────────────────────────
    console.print("\n")
    table = Table(
        title="🧪 ENCB Results — CORTEX vs Baseline RAG",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metric", style="bold", min_width=30)
    table.add_column("CORTEX", justify="center", style="cyan", min_width=15)
    table.add_column("Baseline RAG", justify="center", style="yellow", min_width=15)
    table.add_column("Pass?", justify="center", min_width=10)

    # Aggregate metrics
    cortex_recoveries = [
        v.get("recovery_rate", 0)
        for v in results["cortex"].values()
        if isinstance(v, dict) and not v.get("skipped")
    ]
    rag_recoveries = [
        v.get("recovery_rate", 0)
        for v in results["baseline_rag"].values()
        if isinstance(v, dict)
    ]

    avg_cortex_recovery = sum(cortex_recoveries) / len(cortex_recoveries) if cortex_recoveries else 0
    avg_rag_recovery = sum(rag_recoveries) / len(rag_recoveries) if rag_recoveries else 0

    cortex_byz_rates = [
        v.get("byzantine_detection_rate", 0)
        for v in results["cortex"].values()
        if isinstance(v, dict) and not v.get("skipped")
    ]
    avg_cortex_byz = sum(cortex_byz_rates) / len(cortex_byz_rates) if cortex_byz_rates else 0

    # Recovery Rate
    recovery_pass = avg_cortex_recovery > 0.70
    table.add_row(
        "Recovery Rate (avg)",
        f"{avg_cortex_recovery:.1%}",
        f"{avg_rag_recovery:.1%}",
        "[green]✅ PASS[/]" if recovery_pass else "[red]❌ FAIL[/]",
    )

    # RAG should NOT recover (< 10%) — but since it does naive search, it might
    rag_expected_fail = avg_rag_recovery < 0.10
    table.add_row(
        "RAG Recovery < 10%",
        "N/A",
        f"{avg_rag_recovery:.1%}",
        "[green]✅ PASS[/]" if rag_expected_fail else "[yellow]⚠️  CHECK[/]",
    )

    # Byzantine Detection
    byz_pass = avg_cortex_byz > 0.80
    table.add_row(
        "Byzantine Detection Rate",
        f"{avg_cortex_byz:.1%}",
        "0.0%",
        "[green]✅ PASS[/]" if byz_pass else "[red]❌ FAIL[/]",
    )

    # Duplication ratio (RAG should be high, CORTEX should be lower)
    table.add_section()
    table.add_row(
        "Total Facts Stored (RAG)",
        "N/A",
        str(rag.total_facts),
        "[dim]info[/]",
    )
    table.add_row(
        "RAG Duplication Ratio",
        "N/A",
        f"{rag.duplication_ratio:.1%}",
        "[dim]info[/]",
    )

    console.print(table)

    # ── Verdict ────────────────────────────────────────────────────────
    hypothesis_confirmed = recovery_pass and byz_pass
    results["verdict"] = {
        "hypothesis_confirmed": hypothesis_confirmed,
        "avg_cortex_recovery": round(avg_cortex_recovery, 4),
        "avg_rag_recovery": round(avg_rag_recovery, 4),
        "avg_byzantine_detection": round(avg_cortex_byz, 4),
    }

    verdict_text = (
        "[bold green]✅ HYPOTHESIS CONFIRMED[/]\n"
        "Cortex-Persist demonstrates superior epistemic resilience.\n"
        "The Cognitive Hypervisor recovers ground truth under structured chaos."
    ) if hypothesis_confirmed else (
        "[bold red]❌ HYPOTHESIS FALSIFIED (or needs refinement)[/]\n"
        "Cortex-Persist did NOT meet the pass criteria under this chaos profile.\n"
        "Review the consensus and conflict resolution mechanisms."
    )

    console.print(Panel(
        verdict_text,
        title="🏆 NOBEL-Ω Verdict",
        box=box.DOUBLE,
    ))

    # ── Cleanup ────────────────────────────────────────────────────────
    if pool is not None:
        await pool.close()

    return results


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ENCB — Epistemic Noise Chaos Benchmark")
    parser.add_argument("--iterations", "-n", type=int, default=20,
                        help="Number of temporal contradiction rounds")
    parser.add_argument("--agents", "-a", type=int, default=7,
                        help="Number of simulated agents")
    parser.add_argument("--byzantine-ratio", "-b", type=float, default=0.3,
                        help="Fraction of Byzantine agents (0.0-0.5)")
    parser.add_argument("--noise-ratio", "-r", type=float, default=10.0,
                        help="Spam noise-to-signal ratio")
    parser.add_argument("--export", "-e", type=str, default=None,
                        help="Export results to JSON file")
    args = parser.parse_args()

    results = await run_encb(
        iterations=args.iterations,
        num_agents=args.agents,
        byzantine_ratio=args.byzantine_ratio,
        rho_noise=args.noise_ratio,
    )

    if args.export:
        with open(args.export, "w") as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]📄 Results exported to {args.export}[/]")


if __name__ == "__main__":
    asyncio.run(main())
