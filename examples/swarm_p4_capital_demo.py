import asyncio
import logging
import time

from rich.console import Console
from rich.panel import Panel

# CORTEX Native Imports
from cortex.swarm.capital_swarm import CapitalSwarmEngine

logger = logging.getLogger("cortex.swarm.p4_demo")
console = Console()

async def run_p4_strike():
    """
    P4: Capital Extraction Swarm (Demo).
    Simulates a strike across Vectors A (Bounties) and B (Talent Arbitrage).
    """
    console.print(
        Panel(
            "[bold #2B3BE5]⚛ CORTEX P4: CAPITAL EXTRACTION START[/bold #2B3BE5]\n"
            "Testing Ouroboros Bucle (Ω-Wealth) with real-time Exergy accounting.",
            expand=False,
            border_style="#2B3BE5"
        )
    )

    # We use CapitalSwarmEngine which orchestrates the Specialists
    engine = CapitalSwarmEngine(
        active_vectors=["A", "B", "M"],
        dry_run=True, # Simulate for demo
    )

    t0 = time.monotonic()
    report = await engine.run()
    duration = time.monotonic() - t0

    console.print(f"\n[bold green]✓ P4 Strike Complete in {duration:.2f}s.[/bold green]")
    console.print(f"[bold white]Total Net Exergy extracted: ${report.total_net_yield:+.2f}[/bold white]")

if __name__ == "__main__":
    try:
        asyncio.run(run_p4_strike())
    except KeyboardInterrupt:
        pass
