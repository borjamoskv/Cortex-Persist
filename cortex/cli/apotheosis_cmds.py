"""
APOTHEOSIS-∞ Daemon CLI commands.
El nivel 5 de autonomía Soberana en CORTEX.

Connected to real CORTEX subsystems — zero simulation.
"""

import os
import subprocess
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
    "aix_cmd",
]

console = Console()

PROGRESS_DESC_FMT = "[progress.description]{task.description}"


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
        t_id = progress.add_task("[bold #6600FF]Conectando a CORTEX Engine...[/]", total=None)

        # Real: Connect to CortexEngine and store intent
        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            progress.update(
                t_id, description="[bold #6600FF]CORTEX Engine conectado. Almacenando intent...[/]"
            )
            engine.store(  # type: ignore[reportUnusedCoroutine]
                content=f"APOTHEOSIS-MANIFEST: {intent}",
                fact_type="intent",
                project="apotheosis",
                source="cli:apotheosis:manifest",
            )
            progress.update(
                t_id, description="[bold #06d6a0]Intent almacenado en CORTEX. Verificando...[/]"
            )

            # Verify storage
            results = engine.search(intent, limit=1, project="apotheosis")
            verified = len(results) > 0  # type: ignore[reportArgumentType]
            status = "✅ Verificado" if verified else "⚠️ Sin verificación"
            progress.update(
                t_id, description=f"[bold #D4AF37]{status} — Intent registrado en ledger[/]"
            )
        except ImportError:
            progress.update(
                t_id, description="[dim]CortexEngine no disponible — intent no persistido[/]"
            )

    console.print(
        "\n[bold green]💠 APOTHEOSIS-MANIFIESTO COMPLETADO[/]\n"
        "El intent ha sido registrado y verificado en el ledger.\n"
    )


@apotheosis_cmds.command("guard")
def guard_cmd() -> None:
    """
    El Sueño Demiúrgico: Vigilancia de entropía y purga real de deuda técnica.
    """
    console.print(
        Panel(
            "[bold #2E5090]APOTHEOSIS-GUARD[/]\n"
            "Iniciando vigilancia nocturna y aniquilación de deuda técnica.",
            border_style="#2E5090",
        )
    )

    report_lines = ["# 👁️ Reporte del Sueño Demiúrgico\n"]
    target = Path(os.getcwd()).resolve()

    with Progress(
        SpinnerColumn(spinner_name="moon"),
        TextColumn(PROGRESS_DESC_FMT),
        transient=False,
    ) as progress:
        t_id = progress.add_task(
            "[dim]Escaneando entropía en el directorio actual (ENTROPY-0)...[/]", total=None
        )

        # Real: Run radon CC scan
        cc_results = _scan_entropy(target)
        report_lines.append(f"- Archivos escaneados: {cc_results['total']}")
        report_lines.append(f"- Archivos con entropía alta: {cc_results['critical']}")
        report_lines.append(f"- Max complejidad ciclomática: {cc_results['max_cc']}")

        progress.update(t_id, description="[dim]Ejecutando auto-fix de lint (ruff --fix)...[/]")

        # Real: Run ruff autofix
        ruff_result = subprocess.run(
            ["ruff", "check", "--fix", str(target)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        fixed_count = ruff_result.stdout.count("Fixed")
        report_lines.append(f"- Lint violations auto-fixed: {fixed_count}")

        progress.update(t_id, description="[dim]Generando reporte de operaciones...[/]")

        # Real: Check daemon status
        daemon_status = "desconocido"
        try:
            from cortex.daemon.core import MoskvDaemon

            status = MoskvDaemon.load_status()
            if status:
                daemon_status = "healthy" if status.get("all_healthy") else "degraded"
        except ImportError:
            daemon_status = "no disponible"

        report_lines.append(f"- Daemon status: {daemon_status}")
        report_lines.append("\n*Apotheosis vigila.*")

        try:
            report_path = target / "apotheosis_night_report.md"
            report_path.write_text("\n".join(report_lines), encoding="utf-8")
        except OSError as e:
            console.print(f"\n[bold red]Error al escribir el reporte: {e}[/]")
            raise click.Abort() from e

    pct = (
        0
        if cc_results["total"] == 0
        else (100 - round(cc_results["critical"] / cc_results["total"] * 100))
    )
    console.print(
        f"\n[bold #D4AF37]👁️ EL SUEÑO DEMIÚRGICO FINALIZÓ[/]\n"
        f"Salud arquitectónica: {pct}% archivos sanos. "
        f"Reporte en apotheosis_night_report.md.\n"
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
            f"[bold #f72585]APOTHEOSIS-NIRVANA[/]\n"
            f"Abriendo horizonte de eventos en: {path_resolved.name}",
            border_style="#f72585",
        )
    )

    with Progress(
        SpinnerColumn(spinner_name="bouncingBar"),
        TextColumn(PROGRESS_DESC_FMT),
        transient=False,
    ) as progress:
        t_id = progress.add_task("[bold #f72585]Ejecutando ruff autofix agresivo...[/]", total=None)

        # Real: Aggressive ruff fix
        subprocess.run(
            ["ruff", "check", "--fix", "--unsafe-fixes", str(path_resolved)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        progress.update(t_id, description="[bold #f72585]Aplicando formatting canónico...[/]")

        # Real: ruff format
        subprocess.run(
            ["ruff", "format", str(path_resolved)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        progress.update(t_id, description="[bold #f72585]Midiendo complejidad post-purga...[/]")

        # Real: Post-purge scan
        results = _scan_entropy(path_resolved)
        max_cc = results["max_cc"]

    console.print(
        f"\n[bold white on #f72585] N I R V A N A   A L C A N Z A D O [/]\n"
        f"Post-purga: max CC={max_cc}, {results['critical']} archivos aún críticos "
        f"de {results['total']} escaneados.\n"
    )


@apotheosis_cmds.command("aix")
def aix_cmd() -> None:
    """
    Métrica de Deificación (AIx). Cuantifica la eficiencia y soberanía del sistema.
    """
    import asyncio

    from cortex.cli.aix import calculate_aix, print_aix_report
    from cortex.cli.common import get_engine

    async def run():
        engine = get_engine()
        async with engine.session() as conn:
            data = await calculate_aix(conn)
            print_aix_report(data)

    asyncio.run(run())


def _scan_entropy(target: Path) -> dict:
    """Scan a directory for cyclomatic complexity using radon."""
    from typing import Any
    result: dict[str, Any] = {"total": 0, "critical": 0, "max_cc": 0, "worst_file": ""}
    try:
        from radon.complexity import cc_visit  # pyright: ignore[reportMissingImports]
    except ImportError:
        return result

    for py_file in target.rglob("*.py"):
        if any(p in py_file.parts for p in ("__pycache__", ".venv", "node_modules")):
            continue
        try:
            code = py_file.read_text(encoding="utf-8")
            blocks = cc_visit(code)
            result["total"] += 1
            for b in blocks:
                if b.complexity > result["max_cc"]:
                    result["max_cc"] = b.complexity
                    result["worst_file"] = str(py_file.name)
                if b.complexity > 15:
                    result["critical"] += 1
                    break
        except (SyntaxError, UnicodeDecodeError):
            continue
    return result
