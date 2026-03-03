from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import _run_async, console, get_engine
from cortex.engine.decalcifier import SovereignDecalcifier
from cortex.songlines.sensor import TopographicSensor


@click.group(name="radar")
def radar_cmds():
    """📡 RADAR-Ω: Sovereign monitoring and architectural enforcement."""
    pass


@radar_cmds.command(name="scan")
@click.option("--path", "-p", default=".", help="Path to scan for ghosts.")
@click.option("--entropy", is_flag=True, help="Include entropy scan from DB.")
def scan(path: str, entropy: bool):
    """Scan the topography for active ghosts and entropy."""
    engine = get_engine()
    sensor = TopographicSensor()

    console.print("[noir.cyber]📡 INICIANDO ESCANEO RADAR-Ω (Protocolo Ω₁)...[/noir.cyber]")

    # 1. Physical Ghosts (Banda G)
    scan_path = Path(path).expanduser().resolve()
    ghosts = sensor.scan_field(scan_path)

    # 2. Epistemic Entropy (Banda E)
    entropy_count = 0
    if entropy:

        async def _get_entropy():
            conn = await engine._get_conn()
            # Stated or low confidence facts are considered entropy/calcification candidates
            cursor = await conn.execute(
                "SELECT count(*) FROM facts WHERE confidence IN ('stated', 'C3', 'C2', 'C1') AND is_tombstoned = 0"
            )
            return (await cursor.fetchone())[0]

        entropy_count = _run_async(_get_entropy())

    # Reporting
    if ghosts:
        table = Table(
            title="[bold yellow]Banda G: FANTASMAS DETECTADOS (RESONANCIA)[/bold yellow]",
            box=None,
            header_style="noir.cyber",
        )
        table.add_column("ID", style="dim")
        table.add_column("Resonance", justify="right")
        table.add_column("Source File", style="blue")
        table.add_column("Intent", style="noir.white")

        for g in ghosts:
            table.add_row(
                g["id"][:8], f"{g['strength']:.2f}", Path(g["source_file"]).name, g["intent"]
            )
        console.print(table)
    else:
        console.print("[dim green]Banda G (Ghosts): Espectro limpio.[/dim green]")

    if entropy:
        if entropy_count > 0:
            console.print(
                f"[noir.gold]Banda E (Entropía): {entropy_count} hechos detectados.[/noir.gold]"
            )
        else:
            console.print("[dim green]Banda E (Entropía): Humildad epistémica activa.[/dim green]")

    # 3. Structural Rules (Leyes Físicas)
    console.print("[dim white]Banda A (Arquitectura): Monitoreo pasivo activo.[/dim white]")

    console.print("\n[noir.violet]/// RADAR-Ω: ESCANEO COMPLETADO ///[/noir.violet]")


@radar_cmds.command(name="prune")
def prune():
    """Execute the 'Poda' (Pruning) of impossible states and entropy (Protocol Ω₂)."""
    engine = get_engine()
    decalcifier = SovereignDecalcifier()

    console.print("[noir.gold]✂️ INICIANDO PODA SOBERANA (Protocolo Ω₂)...[/noir.gold]")

    async def _do_prune():
        conn = await engine._get_conn()
        # 1. Decalcify: apply decay logic and tombstone terminal entropy
        count = await decalcifier.decalcify_cycle(conn)
        return count

    pruned_count = _run_async(_do_prune())

    if pruned_count > 0:
        console.print(
            f"[bold green]Se han purgado {pruned_count} hechos en entropía terminal.[/bold green]"
        )
    else:
        console.print("[dim]No se encontraron estados para purgar en esta iteración.[/dim]")

    console.print(
        Panel(
            "[white]La poda ha reforzado las leyes físicas del sistema. "
            "La entropía retrocede.[/white]",
            title="[bold green]ESTADO OPTIMIZADO[/bold green]",
            border_style="green",
        )
    )
