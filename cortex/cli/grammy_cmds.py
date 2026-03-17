"""
CLI Commands for GRAMMY-Ω.
Sovereign Electronic Music Production.
"""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from cortex.extensions.music_engine.orchestrator import GRAMMYOrchestrator, TrackContext, TrackState

console = Console()


@click.group(name="grammy", help="🎵 GRAMMY-Ω: Producción de música electrónica soberana.")
def grammy_cmds():
    """Grupo de comandos para GRAMMY-Ω."""
    pass


@grammy_cmds.command("produce")
@click.argument("title")
@click.option(
    "--concept", default="Avant-garde electronic masterpiece", help="Concepto del álbum/track."
)
@click.option("--bpm", default=120, type=int, help="BPM objetivo.")
@click.option("--key", default="C minor", help="Escala musical.")
def produce_cmd(title, concept, bpm, key):
    """
    Dispara el pipeline de producción de GRAMMY-Ω para un nuevo track.
    """
    console.print(
        Panel(
            f"[bold #CCFF00]GRAMMY-Ω PRODUCTION CORE[/]\n"
            f"Track: [white]{title}[/]\n"
            f"Concepto: [italic]{concept}[/]\n"
            f"Target: [bold]{bpm} BPM | {key}[/]",
            border_style="#CCFF00",
        )
    )

    async def run():
        orchestrator = GRAMMYOrchestrator()
        await orchestrator.initialize_album(title="Singularity", concept=concept)

        track = TrackContext(
            id=f"track_{title.lower().replace(' ', '_')}",
            title=title,
            bpm=bpm,
            key=key,
            state=TrackState.CONCEPT,
        )

        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=False,
        ) as progress:
            task_id = progress.add_task(
                "[bold #6600FF]Iniciando Pipeline de Síntesis...[/]", total=None
            )

            # Hook para reportar estados desde el orquestador
            # (En una versión Pro usaríamos señales de CORTEX)

            progress.update(
                task_id, description="[bold #6600FF]Generando matrices acústicas Ξ...[/]"
            )
            result_track = await orchestrator.run_pipeline(track)

            progress.update(task_id, description="[bold #06d6a0]Pipeline completado ✓[/]")

        console.print("\n[bold green]✓ Producción finalizada con éxito.[/]")
        console.print(f"GRI Score: [bold #CCFF00]{result_track.gri_score:.2f}[/]")
        console.print(f"Estado Final: {result_track.state.value}")

    asyncio.run(run())


if __name__ == "__main__":
    grammy_cmds()
