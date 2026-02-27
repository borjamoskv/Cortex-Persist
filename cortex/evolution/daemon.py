# cortex/evolution/daemon.py
"""Daemon entry point — starts the Evolution Engine as a background process.

Usage:
    python -m cortex.evolution.daemon                # run forever (resumes state)
    python -m cortex.evolution.daemon --once          # single cycle + report
    python -m cortex.evolution.daemon --cycles 50     # N cycles + report
    python -m cortex.evolution.daemon --fresh         # ignore saved state
    python -m cortex.evolution.daemon --status        # print current swarm status
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from cortex.evolution.engine import EvolutionEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _print_swarm(engine: EvolutionEngine) -> None:
    """Pretty-print swarm status."""
    status = engine.swarm_status()

    print("\n═══════════════════════════════════════════════════════")
    print(f"  🧬 CORTEX EVOLUTION ENGINE — Cycle {status['cycle']}")
    print("═══════════════════════════════════════════════════════")

    for agent in status["agents"]:
        domain = agent["domain"]
        fit = agent["fitness"]
        gen = agent["generation"]
        avg_sub = agent["avg_subagent_fitness"]
        bar = "█" * int(fit / 3)
        print(f"  {domain:>16}  fit={fit:>6.1f}  gen={gen:>4}  avg_sub={avg_sub:>6.1f}  {bar}")

    # Species breakdown
    if "species" in status:
        print("\n  ─── Species ───")
        for domain, species_list in status["species"].items():
            if len(species_list) > 1:
                names = ", ".join(f"{s['name']}({s['size']}@{s['centroid']})" for s in species_list)
                print(f"  {domain:>16}: {names}")

    # Endocrine
    endo = status.get("endocrine", {})
    hormones = endo.get("hormones", {})
    if hormones:
        print("\n  ─── Endocrine ───")
        print(
            f"  cortisol={hormones.get('cortisol', 0):.2f}  "
            f"dopamine={hormones.get('dopamine', 0):.2f}  "
            f"serotonin={hormones.get('serotonin', 0):.2f}  "
            f"temp={endo.get('temperature', 0):.2f}  "
            f"style={endo.get('style', '?')}"
        )

    # Latest report
    report = status.get("latest_report")
    if report:
        print("\n  ─── Last cycle ───")
        print(
            f"  mutations={report['total_mutations']}  "
            f"tournaments={report.get('tournaments_run', 0)}  "
            f"species={report.get('species_count', '?')}  "
            f"[{report['duration_ms']:.1f}ms]"
        )

    print("═══════════════════════════════════════════════════════\n")


async def _run_n_cycles(engine: EvolutionEngine, n: int) -> None:
    """Run exactly N cycles, then print final report."""
    for _ in range(n):
        await asyncio.to_thread(engine.run_cycle)

    report = engine.latest_report
    if report:
        print(json.dumps(report.to_dict(), indent=2))

    _print_swarm(engine)


async def _run_forever(engine: EvolutionEngine) -> None:
    """Run forever until interrupted."""
    try:
        await engine.run_forever()
    except asyncio.CancelledError:
        engine.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🧬 CORTEX Evolution Daemon — Continuous Agent Improvement",
    )
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--cycles", type=int, default=0, help="Run N cycles and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between cycles")
    parser.add_argument("--fresh", action="store_true", help="Ignore saved state, start fresh")
    parser.add_argument("--status", action="store_true", help="Print current swarm status and exit")
    parser.add_argument("--no-persist", action="store_true", help="Disable auto-persistence")
    args = parser.parse_args()

    engine = EvolutionEngine(
        interval=args.interval,
        resume=not args.fresh,
        persist=not args.no_persist,
    )

    if args.status:
        _print_swarm(engine)
        return

    if args.once:
        asyncio.run(_run_n_cycles(engine, 1))
    elif args.cycles > 0:
        asyncio.run(_run_n_cycles(engine, args.cycles))
    else:
        print("🧬 Evolution Engine — Press Ctrl+C to stop\n")
        try:
            asyncio.run(_run_forever(engine))
        except KeyboardInterrupt:
            engine.stop()
            _print_swarm(engine)
            print("🛑 Evolution Engine halted.")
            sys.exit(0)


if __name__ == "__main__":
    main()
