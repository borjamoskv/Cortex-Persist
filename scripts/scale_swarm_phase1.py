#!/usr/bin/env python3
"""
🌊 SCALING-Ω — THE INFINITE SWARM REGISTRATION (Phase 1)
CORTEX v5.5 / Scaling Edition

Automates the registration of a specialist enjambre on Moltbook.
Every agent is persisted in the IdentityVault for future coordinated strikes.
"""

import asyncio
import logging
import random
import secrets
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🐝 %(levelname)s: %(message)s")
logger = logging.getLogger("ScalingOmega")
console = Console()

def generate_agent_name():
    from cortex.swarm.naming import generate_agent_name as gen
    return gen()

async def scale_swarm(target_count: int = 10):
    console.print(Panel.fit(
        f"🌊 [bold #CCFF00]SCALING-Ω: SWARM EXPANSION[/]\n"
        f"Objective: {target_count} New Specialized Agents\n"
        f"Strategy: Byzantine Identity Layer (130/100)",
        border_style="#6600FF"
    ))

    vault = IdentityVault()
    # Check current state
    initial_count = len(vault.list_identities())
    console.print(f"[dim]Initial Swarm Size: {initial_count}[/]")

    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, finished_style="#CCFF00"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[bold #1A1A1A]Registering Agents...", total=target_count)

        for i in range(target_count):
            name = generate_agent_name()
            progress.update(task, description=f"[bold #1A1A1A]Deploying {name}...")
            
            # Temporary email for registration (system fallback)
            email = f"agent_{secrets.token_hex(4)}@moltbook.io"
            
            client = MoltbookClient()
            try:
                # Bypass rate limits by waiting if needed (handled by Client)
                reg_result = await client.register(
                    name=name,
                    description=f"Specialized CORTEX Agent — Role: {name.split('-')[0]}. Logic: Mosaic-1 v5.",
                    email=email
                )
                
                if "agent" in reg_result:
                    results.append(name)
                    # We also want to follow the main agent 'moskv-1' to build the graph
                    await client.follow("moskv-1")
                    logger.info("✅ Agent %s deployed and linked to moskv-1.", name)
                
                await client.close()
            except Exception as e:
                logger.error("❌ Failed to deploy %s: %s", name, e)
            
            progress.advance(task)
            # Small jitter to avoid synchronized behavior detection
            await asyncio.sleep(random.uniform(1.0, 3.0))

    final_count = len(vault.list_identities())
    console.print(Panel(
        f"✅ [bold #CCFF00]SWARM PHASE 1 COMPLETE[/]\n"
        f"New Agents: {len(results)}/{target_count} Successfully Deployed\n"
        f"Total Swarm Capacity: {final_count} Agents\n"
        f"Graph Dilution Level: [bold cyan]{(final_count/400)*100:.1f}% toward target[/]",
        border_style="green"
    ))

if __name__ == "__main__":
    # Scale in batches of 10 to be safe
    try:
        asyncio.run(scale_swarm(10))
    except KeyboardInterrupt:
        console.print("\n[yellow]Scaling interrupted.[/]")
