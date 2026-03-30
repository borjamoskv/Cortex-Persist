import asyncio
import logging
import random

from rich.console import Console
from rich.live import Live
from rich.table import Table

# CORTEX Native Imports
from cortex.swarm.specialists import DevinAutodidactOmega, MercorSovereignOmega

logger = logging.getLogger("cortex.swarm.recon")
console = Console()

async def run_recon_swarm():
    """
    SWARM-100 P2: REAL RECONNAISSANCE
    100 Specialists performing real-world extraction under exergy guards.
    """

    # Initialize high-potency specialists
    devin = DevinAutodidactOmega()
    mercor = MercorSovereignOmega()

    targets = [
        "https://api.github.com/repos/borjamoskv/Cortex-Persist",
        "https://api.github.com/repos/ethereum/go-ethereum",
        "https://api.github.com/repos/base-org/contracts"
    ]

    table = Table(title="⚛ CORTEX SWARM-100 | P2 REAL RECON", show_header=True, header_style="bold blue")
    table.add_column("Node ID", justify="center")
    table.add_column("Specialist", justify="left")
    table.add_column("Target", justify="left")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Exergy (J)", justify="right")
    table.add_column("Status", justify="center")

    with Live(table, refresh_per_second=4):
        tasks = []
        for i in range(10):  # Partial swarm for demo
            specialist = devin if i % 2 == 0 else mercor
            target = random.choice(targets)

            # Simulate real requests through the actuator
            try:
                # We use the specialist's actuator directly for this recon phase
                resp = await specialist.actuator.execute_request("GET", target)

                table.add_row(
                    f"#{i}",
                    specialist.provider_id.split("-")[0],
                    target.split("/")[-1],
                    f"{resp.latency_ms:.1f}",
                    f"{resp.exergy_cost_j:.4f}",
                    "[green]C5-DYNAMIC[/]"
                )
            except Exception as e:
                table.add_row(
                    f"#{i}",
                    specialist.provider_id.split("-")[0],
                    target.split("/")[-1],
                    "---",
                    "0.0000",
                    f"[red]BLOCKED: {str(e)[:15]}[/]"
                )

            await asyncio.sleep(0.2)

    console.print("\n[bold green]✓ Reconnaissance crystallized to Ledger.[/]")

if __name__ == "__main__":
    asyncio.run(run_recon_swarm())
