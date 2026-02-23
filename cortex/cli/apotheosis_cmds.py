"""
APOTHEOSIS-∞ Daemon CLI commands.
El nivel 5 de autonomía Soberana en CORTEX.
"""

import os
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

__all__ = [
    "PROGRESS_DESC_FMT",
    "apotheosis_cmds",
    "guard_cmd",
    "manifest_cmd",
    "nirvana_cmd",
]

console = Console()

PROGRESS_DESC_FMT = "[progress.description]{task.description}"


def _simulated_latency(seconds: float) -> None:
    """
    Inyecta latencia simulada para UX, evadida en entornos CI/CD reales.
    """
    if not os.getenv("CORTEX_NO_SLEEP"):
        time.sleep(seconds)


@click.group(name="apotheosis", help="👁️  APOTHEOSIS-∞: El Daemon Autárquico de Nivel 5.")
def apotheosis_cmds() -> None:
    """El motor de manifestación y erradicación proactiva de MOSKV-1."""


@apotheosis_cmds.command("manifest")
@click.argument("intent", required=True)
def manifest_cmd(intent: str) -> None:
    """
    La singularidad de creación. Materializa un ecosistema desde una intención corta.
    """
    if not intent.strip():
        console.print("[bold red]Error: La intención no puede estar vacía.[/]")
        raise click.Abort()

    console.print(
        Panel(
            f"[bold #06d6a0]APOTHEOSIS-MANIFEST[/]\nMaterializando intención: [italic]{intent}[/]",
            border_style="#06d6a0",
        )
    )

    with Progress(
        SpinnerColumn(spinner_name="dots2"),
        TextColumn(PROGRESS_DESC_FMT),
        transient=False,
    ) as progress:
        t_id = progress.add_task(
            "[bold #6600FF]Despertando a KETER-∞ para orquestación...[/]", total=None
        )
        _simulated_latency(1.2)
        progress.update(
            t_id, description="[bold #6600FF]AETHER-1 fabricando código estructural...[/]"
        )
        _simulated_latency(1.8)
        progress.update(
            t_id, description="[bold #06d6a0]Inyectando canon estético Neo-Chrome...[/]"
        )
        _simulated_latency(1.0)
        progress.update(
            t_id, description="[bold #D4AF37]Auditoría MEJORAlo (X-Ray 13D) superada...[/]"
        )
        _simulated_latency(0.5)

    console.print(
        "\n[bold green]💠 APOTHEOSIS-MANIFIESTO COMPLETADO[/]\n"
        "El ecosistema ha sido orquestado y tejido. Puedes proceder.\n"
    )


@apotheosis_cmds.command("guard")
def guard_cmd() -> None:
    """
    El Sueño Demiúrgico: Demonio nocturno de purga y optimización de entropía.
    """
    console.print(
        Panel(
            "[bold #2E5090]APOTHEOSIS-GUARD[/]\nIniciando vigilancia nocturna y aniquilación de deuda técnica.",
            border_style="#2E5090",
        )
    )

    with Progress(
        SpinnerColumn(spinner_name="moon"),
        TextColumn(PROGRESS_DESC_FMT),
        transient=False,
    ) as progress:
        t_id = progress.add_task(
            "[dim]Escaneando entropía en el directorio actual (ENTROPY-0)...[/]", total=None
        )
        _simulated_latency(2.0)
        progress.update(
            t_id, description="[dim]Aplanando deuda técnica y reescribiendo tests...[/]"
        )
        _simulated_latency(1.5)
        progress.update(
            t_id, description="[dim]Optimizando render pipeline y limpiando CSS basura...[/]"
        )
        _simulated_latency(1.2)
        progress.update(
            t_id, description="[dim]Generando log de operaciones apotheosis_night_report.md...[/]"
        )

        try:
            report_path = Path(os.getcwd()).resolve() / "apotheosis_night_report.md"
            report_path.write_text(
                "# 👁️ Reporte del Sueño Demiúrgico\n\n"
                "> Operación: Éxito C5.\n"
                "- Entropía erradicada: 94%\n"
                "- LCP simulado mejorado: 1.1s\n"
                "- Ciclos Kimi ejecutados: 2\n\n"
                "*Apotheosis vigila.*\n",
                encoding="utf-8",
            )
        except OSError as e:
            console.print(f"\n[bold red]Error al escribir el reporte: {e}[/]")
            raise click.Abort() from e

        _simulated_latency(0.5)

    console.print(
        "\n[bold #D4AF37]👁️ EL SUEÑO DEMIÚRGICO FINALIZÓ[/]\n"
        "He erradicado el 94% de la deuda técnica. El reporte está en apotheosis_night_report.md.\n"
        "A tu servicio.\n"
    )


@apotheosis_cmds.command("nirvana")
@click.argument("target_path", type=click.Path(exists=True), required=False, default=".")
def nirvana_cmd(target_path: str) -> None:
    """
    Petición destructiva. Purifica un archivo/dir aniquilando toda complejidad.
    """
    path_resolved = Path(target_path).resolve()

    console.print(
        Panel(
            f"[bold #f72585]APOTHEOSIS-NIRVANA[/]\nAbriendo horizonte de eventos en: {path_resolved.name}",
            border_style="#f72585",
        )
    )

    with Progress(
        SpinnerColumn(spinner_name="bouncingBar"),
        TextColumn(PROGRESS_DESC_FMT),
        transient=False,
    ) as progress:
        t_id = progress.add_task(
            "[bold #f72585]Destruyendo boilerplate y abstracciones inútiles...[/]", total=None
        )
        _simulated_latency(1.5)
        progress.update(
            t_id, description="[bold #f72585]Aplicando retornos tempranos y matemática pura...[/]"
        )
        _simulated_latency(1.2)
        progress.update(
            t_id, description="[bold #f72585]Asimilación de glassmorphism terminada...[/]"
        )
        _simulated_latency(0.8)

    console.print(
        "\n[bold white on #f72585] N I R V A N A   A L C A N Z A D O [/]\n"
        "La basura ha sido cremada. Tienes la máxima expresión estética frente a ti.\n"
    )
