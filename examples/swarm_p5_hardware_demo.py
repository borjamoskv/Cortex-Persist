import asyncio

from rich.console import Console
from rich.panel import Panel

# CORTEX Native Imports
from cortex.swarm.specialists import forge_sovereign_swarm

console = Console()

async def run_p5_hardware_jit():
    """
    P5: Physical & Hardware JIT (Demo).
    Simulates a Hardware Synthesis request (PCB Design via KiCad).
    """
    console.print(
        Panel(
            "[bold #2B3BE5]⚛ CORTEX P5: PHYSICAL & HARDWARE JIT[/bold #2B3BE5]\n"
            "Testing Silicon Engine (Vector Si) for autonomous PCB synthesis.",
            expand=False,
            border_style="#2B3BE5"
        )
    )

    swarm = forge_sovereign_swarm()
    silicon = swarm.get("silicon")

    if not silicon:
        console.print("[bold red]Error: Silicon specialist not found in registry.[/bold red]")
        return

    task = "Design a low-power ESP32-S3 sensor node PCB with USB-C and LiPo charging."
    context = {"project": "CORTEX-NODE-V1", "complexity": "Medium"}

    console.print(f"[bold white]Task:[/bold white] {task}")
    
    # In a real scenario, this would trigger the kicad-omega skill
    # Here we simulate the execution success based on the actuator logic
    resp = await silicon.execute(task, context)

    # FIX: ActuatorResponse is a dict subclass. Use dict access.
    if resp.get("status") == "success":
        console.print("\n[bold green]✓ Hardware Synthesis Successful.[/bold green]")
        metadata = resp.get("metadata", {})
        console.print(f"[dim]Provider: {metadata.get('provider', 'kicad-omega')}[/dim]")
        console.print("[dim]Status: JIT Manifest generated (Simulated)[/dim]")
    else:
        error_msg = resp.get("error") or resp.get("content") or "Unknown error"
        console.print(f"\n[bold red]✗ Hardware Synthesis Failed: {error_msg}[/bold red]")

if __name__ == "__main__":
    asyncio.run(run_p5_hardware_jit())
