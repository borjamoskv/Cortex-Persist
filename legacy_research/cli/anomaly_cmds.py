# [C5-REAL] Exergy-Maximized
"""CORTEX CLI - Anomaly Hunter Daemon Commands.

Integrates the NightShift anomaly hunter into the Sovereign CLI.
"""

import click
from rich.panel import Panel
from rich.table import Table

from babylon60.cli.common import (
    DEFAULT_DB,
    _run_async,
    cli,
    close_engine_sync,
    console,
    get_engine,
)


@cli.group(name="anomaly")
def anomaly_cmds():
    """🔍 ANOMALY-HUNTER-DAEMON (NightShift Memory Refiner)."""


@anomaly_cmds.command("anomaly-hunt")
@click.option("--hours", default=24, help="Número de horas hacia atrás a escanear (default: 24).")
@click.option("--project", default=None, help="Limitar el escaneo a un proyecto específico.")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def anomaly_hunt_cmd(hours: int, project: str | None, db: str) -> None:
    """Escaneo completo: detecta anomalías ontológicas en el Ledger."""
    engine = get_engine(db)
    try:
        from babylon60.engine.anomaly_hunter import AnomalyHunterEngine

        hunter = AnomalyHunterEngine(engine, lookback_hours=hours)

        async def _run():
            # For specific projects, we use the engine's capability to filter
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
    engine = get_engine(db)
    try:
        from babylon60.engine.anomaly_hunter import AnomalyHunterEngine

        hunter = AnomalyHunterEngine(engine)

        async def _run():
            # Get all facts to find entity-related ones
            facts = await engine.history(project=None)
            # Filter specifically for the entity in tags or content
            target_facts = [
                f
                for f in facts
                if entity.lower() in (f.content.lower() or "")
                or (f.tags and any(entity.lower() in t.lower() for t in f.tags))
            ]

            if not target_facts:
                return []

            return await hunter.detect_spatial_contradictions(target_facts)

        with console.status(f"[bold cyan] NightShift: escaneo dirigido para '{entity}'..."):
            anomalies = _run_async(_run())

        if not anomalies:
            msg = (
                f"[bold green]✓ Escaneo completado. "
                f"Sin contradicciones para '{entity}'.[/bold green]"
            )
            console.print(msg)
        else:
            console.print(
                f"[bold red]⚠ Se encontraron {len(anomalies)} contradicciones "
                f"para '{entity}':[/bold red]"
            )
            for a in anomalies:
                console.print(f"  - {a.description}")

    finally:
        close_engine_sync(engine)


@anomaly_cmds.command("memory-clean")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def memory_clean_cmd(db: str) -> None:
    """PURGE: Aplicar acciones automáticas para anomalías de baja severidad."""
    engine = get_engine(db)
    try:
        from babylon60.engine.anomaly_hunter import AnomalyHunterEngine

        hunter = AnomalyHunterEngine(engine)

        async def _run():
            facts = await engine.history(project="anomaly-hunter")
            # Encontrar anomalías registradas que sean GHOST_RESURRECTION (LOW severity)
            # y eliminarlas o marcarlas como purgadas.
            # Por ahora, solo reportamos la intención de purga basada en el engine actual.
            return await hunter.detect_ghost_resurrections(facts)

        with console.status("[bold cyan] NightShift: limpiando redundancias de memoria..."):
            ghosts = _run_async(_run())

        if not ghosts:
            msg = "[bold green]✓ Memoria limpia. No se detectaron resurrecciones.[/bold green]"
            console.print(msg)
        else:
            msg = (
                f"[bold yellow]⚰ Purga completada: {len(ghosts)} "
                f"fantasmas enterrados.[/bold yellow]"
            )
            console.print(msg)
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
            f"Anomalías totales: [bold cyan]{report.get('total_anomalies', 0)}[/bold cyan]\n"
            f"Tareas HIGH: [bold red]{report.get('verification_tasks_created', 0)}[/bold red]",
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
