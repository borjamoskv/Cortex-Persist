import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB


@click.group(name="cuatrida")
def cuatrida_group():
    """Monitor sovereign ABCD dimensions (The Cuátrida Entity)."""


@cuatrida_group.command(name="status")
@click.option("--project", default=None, help="Filter by project name.")
@click.option("--db", default=DEFAULT_DB, help="Database path.")
@click.pass_context
def status(ctx, project, db):
    """Display real-time ABCD metrics and honor scores."""
    import asyncio

    async def run():
        from cortex.database.pool import CortexConnectionPool
        from cortex.engine_async import AsyncCortexEngine

        pool = CortexConnectionPool(db, read_only=False)
        await pool.initialize()
        engine = AsyncCortexEngine(pool, db)

        orchestrator = engine.cuatrida

        if project:
            await orchestrator.zero_friction_sync(project)

        metrics = orchestrator.metrics

        console = Console()

        console.print(Panel.fit(
            "[bold #CCFF00]CUÁTRIDA SOBERANA (ABCD)"
            "[/bold #CCFF00] - Status Report",
            border_style="#6600FF",
            box=box.DOUBLE,
        ))

        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold #CCFF00",
            border_style="grey37",
        )
        table.add_column("DIM", justify="center", style="bold")
        table.add_column("DIMENSION", width=25)
        table.add_column("METRIC", justify="right")
        table.add_column("STATUS", justify="center")

        # Dimension A — Friction
        a_status = (
            "🟢 ZERO" if metrics.latency_ms < 100 else "🟡 KINETIC"
        )
        table.add_row(
            "A", "Fricción Cero (Latencia)",
            f"{metrics.latency_ms:.2f}ms", a_status,
        )

        # Dimension B — Temporal
        table.add_row(
            "B", "Soberanía Temporal (Decisions)",
            str(metrics.decision_count), "🔵 IMMUTABLE",
        )

        # Dimension C — Aesthetic Honor
        c_style = (
            "bold #CCFF00"
            if metrics.aesthetic_honor >= 90
            else "bold #FF3366"
        )
        c_status = (
            "🏆 HONORABLE"
            if metrics.aesthetic_honor >= 90
            else "⚠️ ENTROPIC"
        )
        table.add_row(
            "C", "Soberanía Estética (Honor)",
            f"[{c_style}]{metrics.aesthetic_honor:.1f}/100"
            f"[/{c_style}]",
            c_status,
        )

        # Dimension D — Computational Respect
        d_status = (
            "🌱 RESPECTFUL"
            if metrics.computational_respect > 0.8
            else "🔥 CONSUMER"
        )
        table.add_row(
            "D", "Gestión Ética (Respeto)",
            f"{metrics.computational_respect:.2f}", d_status,
        )

        console.print(table)

        # Omega Pulse
        omega_score = (
            metrics.finitud_density
            + (metrics.aesthetic_honor / 100)
            + metrics.computational_respect
        ) / 3
        console.print(
            f"\n[bold #6600FF]Ω NODAL PULSE:[/bold #6600FF] "
            f"[white]{omega_score:.4f}[/white] | "
            "[italic #555]Singularity Convergence Active"
            "[/italic #555]",
        )

        await pool.close()

    asyncio.run(run())
