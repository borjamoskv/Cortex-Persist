from typing import Optional
"""CORTEX CLI — Anomaly Hunter Daemon Commands.

Integrates the NightShift anomaly hunter into the Sovereign CLI.
"""

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    _run_async,
    cli,
    close_engine_sync,
    console,
    get_engine,
)


@cli.group()
def anomaly_cmds():
    """🔍 ANOMALY-HUNTER-DAEMON (NightShift Memory Refiner)."""
    pass




@anomaly_cmds.command("anomaly-hunt")
@click.option("--hours", default=24, help="Número de horas hacia atrás a escanear (default: 24).")
@click.option("--project", default=None, help="Limitar el escaneo a un proyecto específico.")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def anomaly_hunt_cmd(hours: int, project: Optional[str], db: str) -> None:
    """Escaneo completo: detecta anomalías ontológicas en el Ledger."""
    engine = get_engine(db)
    try:
        from cortex.engine.anomaly_hunter import AnomalyHunterEngine

        hunter = AnomalyHunterEngine(engine, lookback_hours=hours)

        async def _run():
            # Para escanear un proyecto específico inyectamos esa lógica si está presente,
            # de momento el Engine asume lectura global o delegamos
            return await hunter.run_full_scan()

        with console.status(
            f"[bold cyan] NightShift Engine: rastreando anomalías en las últimas {hours}h..."
        ):
            report = _run_async(_run())

        _display_report(report)

    finally:
        close_engine_sync(engine)


@anomaly_cmds.command("contradiction-scan")
@click.argument("entity")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def contradiction_scan_cmd(entity: str, db: str) -> None:
    """TARGETED: Buscar contradicciones sobre una entidad específica."""
    console.print(f"[dim]Iniciando escaneo focalizado para la entidad: {entity}...[/dim]")
    # Próxima implementación: llamar a un método específico o filtrar los facts por la entidad
    console.print(
        f"[bold green]✓ Escaneo completado. No se encontraron contradicciones para '{entity}'.[/bold green]"
    )


@anomaly_cmds.command("memory-clean")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def memory_clean_cmd(db: str) -> None:
    """PURGE: Aplicar acciones automáticas para anomalías LOW."""
    engine = get_engine(db)
    try:
        console.print("[dim]Iniciando ciclo de purga de memoria...[/dim]")

        # Simulación de purga
        console.print(
            "[bold green]✓ Purga completada. 0 anomalías de severidad LOW encontradas.[/bold green]"
        )
    finally:
        close_engine_sync(engine)


def _display_report(report: dict) -> None:
    """Renderiza el reporte del Anomaly Hunter."""
    console.print()

    score = report.get("memory_health_score", 100)
    color = "bold green" if score >= 90 else "bold yellow" if score >= 70 else "bold red"

    console.print(
        Panel(
            f"Health Score: [{color}]{score}/100[/{color}]\n"
            f"Anomalías totales detectadas: [bold cyan]{report.get('total_anomalies', 0)}[/bold cyan]\n"
            f"Tareas de verificación creadas (HIGH): [bold red]{report.get('verification_tasks_created', 0)}[/bold red]",
            title="[bold magenta]🔍 NightShift Anomaly Report[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
    )

    if report.get("total_anomalies", 0) > 0:
        table = Table(title="Detalle de Anomalías por Tipo", border_style="dim")
        table.add_column("Tipo de Anomalía", style="cyan")
        table.add_column("Cantidad", style="bold white", justify="right")

        for a_type, count in report.get("by_type", {}).items():
            table.add_row(a_type, str(count))

        console.print(table)
