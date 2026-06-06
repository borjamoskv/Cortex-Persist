import logging

from rich.console import Console
from rich.panel import Panel

from cortex.engine.omega_daemon import OmegaKernel

console = Console()
logger = logging.getLogger(__name__)

async def cmd_omega_start(tick_rate: int = 60, auto_push: bool = False):
    """
    Inicia el metabolismo de CORTEX (Omega Singularity).
    """
    console.print(Panel("[bold green]CORTEX v10.0 - OMEGA SINGULARITY[/bold green]\n"
                        "Inicializando Metabolismo Digital...", border_style="green"))
    
    kernel = OmegaKernel(tick_rate_seconds=tick_rate, auto_push=auto_push)
    
    try:
        await kernel.run_forever()
    except KeyboardInterrupt:
        console.print("\n[bold red]Terminación manual detectada. Hibernando Omega Daemon...[/bold red]")
        kernel.stop()

def cmd_omega_status():
    """
    Consulta el estado del metabolismo (si estuviera en un background daemon real).
    """
    console.print("[dim]Omega Daemon status request (Stub)[/dim]")
    # En un daemon real, nos comunicaríamos vía socket/IPC para consultar el estado.
    console.print("[green]OmegaKernel is available for instantiation.[/green]")
