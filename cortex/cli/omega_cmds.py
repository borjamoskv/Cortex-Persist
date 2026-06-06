import asyncio
import logging
import click
from rich.console import Console
from rich.panel import Panel

from cortex.engine.omega_daemon import OmegaKernel
from cortex.cli.common import cli

console = Console()
logger = logging.getLogger(__name__)

@cli.group("omega")
def omega_cmds():
    """Mega Hito 38: Omega Singularity (CORTEX v10.0 Metabolism)."""
    pass

@omega_cmds.command("start")
@click.option("--tick-rate", default=60, help="Latidos por segundo del metabolismo.")
@click.option("--auto-push", is_flag=True, help="Auto-push en cada mutación.")
def cmd_omega_start(tick_rate: int, auto_push: bool):
    """
    Inicia el metabolismo de CORTEX (Omega Singularity).
    """
    console.print(Panel("[bold green]CORTEX v10.0 - OMEGA SINGULARITY[/bold green]\n"
                        "Inicializando Metabolismo Digital...", border_style="green"))
    
    kernel = OmegaKernel(tick_rate_seconds=tick_rate, auto_push=auto_push)
    
    try:
        asyncio.run(kernel.run_forever())
    except KeyboardInterrupt:
        console.print("\n[bold red]Terminación manual detectada. Hibernando Omega Daemon...[/bold red]")
        kernel.stop()

@omega_cmds.command("status")
def cmd_omega_status():
    """
    Consulta el estado del metabolismo.
    """
    console.print("[dim]Omega Daemon status request (Stub)[/dim]")
    console.print("[green]OmegaKernel is available for instantiation.[/green]")
