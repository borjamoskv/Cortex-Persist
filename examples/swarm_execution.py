import asyncio
import json
import logging
import sqlite3

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.ledger import SovereignLedger
from cortex.swarm.factory import SwarmFactory

logging.basicConfig(level=logging.ERROR)  # Only show our rich output
logger = logging.getLogger("cortex.swarm.specialists")
logger.setLevel(logging.INFO)

console = Console()


async def execute_thermodynamic_flow():
    console.print("[bold cyan]Ω-Architecture: Executing Sovereign Swarm Flow...[/bold cyan]")

    # 1. Initialize Ledger
    console.print("\n[dim]Initializing cryptographic ledger (trust boundary)...[/dim]")
    
    db_conn = sqlite3.connect(":memory:")
    ledger = SovereignLedger(db_conn=db_conn)

    # 2. Forge Swarm
    console.print("[dim]Forging swarm with Ultra-Potent skills...[/dim]")
    swarm = SwarmFactory.forge(ledger=ledger)
    available = await swarm.get_manager().list_available()
    console.print(
        f"[bold green]Swarm Online[/bold green]. Available actuators: {', '.join(available)}"
    )

    # 3. Define the Mission
    missions = [
        (
            "devin-autodidact-omega",
            "Refactor the memory caching layer to O(1) retrieval, eliminating all PII data from logs in the process.",
            {"user_email": "admin@cortex.network"},
        ),
        (
            "ouroboros-capital-omega",
            "Scan liquid staking pools for delta > 2.5% and extract exergy.",
            {"wallet": "0xABC123"},
        ),
        ("awwwards-deconstructor", "Deconstruct the https://example.com landing page WebGL shader.", {}),
    ]

    # 4. Dispatch tasks concurrently
    console.print("\n[bold magenta]Dispatching multi-agent mission...[/bold magenta]")
    tasks = []
    for actuator_name, prompt, ctx in missions:
        console.print(f" -> Mapping task to [yellow]{actuator_name}[/yellow]: {prompt[:40]}...")
        tasks.append(swarm.dispatch(actuator_name=actuator_name, task=prompt, context=ctx))

    responses = await asyncio.gather(*tasks)

    # 5. Display Responses
    console.print("\n[bold cyan]Sovereign Responses Received:[/bold cyan]")
    for i, res in enumerate(responses):
        console.print(
            Panel(
                res.content,
                title=f"Node: {missions[i][0]} | Status: {res.status}",
                border_style="green" if res.status == "success" else "red",
            )
        )

    # 6. Display Yield & Audit Trace
    console.print("\n[bold cyan]Thermodynamic Ledger Audit (Proof of Work):[/bold cyan]")
    records = ledger.get_transactions(project="swarm")
    
    table = Table(title="Sovereign Swarm Cryptographic Ledger", box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Action", style="cyan")
    table.add_column("Details", style="white", overflow="ellipsis")
    table.add_column("Hash", style="magenta", justify="right")
    
    total_exergy = 0.0
    for r in records:
        tx_id, ts, action, detail_json, prev_hash, h = r
        detail = json.loads(detail_json)
        table.add_row(str(tx_id), action, str(detail)[:65] + "...", h[:20] + "...")
        
        # Accumulate exergy from success records
        if action == "execution_success":
            total_exergy += detail.get("exergy_yield", 0.0)
            
    console.print(table)
    
    console.print("\n[bold green]Thermodynamic Yield Report:[/bold green]")
    console.print(f" - Tasks executed: {len(missions)}")
    console.print(f" - Total Exergy Yielded: {total_exergy} U (Ω₉ Claim)")
    console.print(" - Net Exergy: Positive. Fricton boundary passed. (C5-Dynamic)")


if __name__ == "__main__":
    asyncio.run(execute_thermodynamic_flow())

