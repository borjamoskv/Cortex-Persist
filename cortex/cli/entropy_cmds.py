"""CLI commands: entropy install-hook, scan, report."""

from __future__ import annotations

import shutil
from pathlib import Path

from cortex.cli import cli, console
from cortex.cli.errors import err_empty_results, err_platform, handle_cli_error

__all__ = ["entropy", "entropy_install_hook", "entropy_report"]


@cli.group()
def entropy():
    """ENTROPY-0 v1.0 — El Guardián de la Deuda Técnica."""
    pass


@entropy.command("install-hook")
def entropy_install_hook():
    """Instala ENTROPY-0 como hook de pre-commit en el repositorio actual."""
    try:
        git_dir = Path.cwd() / ".git"
        if not git_dir.exists():
            err_platform("No se encontró un repositorio Git en este directorio.")
            return

        hook_dir = git_dir / "hooks"
        hook_dir.mkdir(exist_ok=True)

        # Ruta del archivo pre-commit
        pre_commit_file = hook_dir / "pre-commit"

        # Ruta del script origen
        import cortex

        source_script = Path(cortex.__file__).parent / "hooks" / "zero_debt.py"

        if not source_script.exists():
            err_platform(f"No se encontró el script zero_debt.py en {source_script}")
            return

        shutil.copy2(source_script, pre_commit_file)
        pre_commit_file.chmod(0o755)

        console.print("[bold green]✅ ENTROPY-0 instalado exitosamente en .git/hooks/pre-commit[/]")
        console.print(
            "[dim]A partir de ahora, ningún commit pasará si la puntuación MEJORAlo es < 90.[/]"
        )
    except (OSError, ValueError, RuntimeError, ImportError) as e:
        handle_cli_error(e, context="installing entropy hook")


@entropy.command("report")
def entropy_report():
    """Genera un reporte del estado de inmunidad del proyecto."""
    console.print("[bold cyan]🔍 Analizando inmunidad del ecosistema...[/]")
    from cortex.daemon.core import MoskvDaemon

    try:
        status_dict = MoskvDaemon.load_status()
        if not status_dict:
            err_empty_results("daemon status", suggestion="Ensure MoskvDaemon is running.")
            return

        alerts = status_dict.get("entropy_alerts", [])
        if not alerts:
            console.print("[bold green]✅ Estado: ENTROPY-0 activo. Cero deuda técnica en vivo.[/]")
        else:
            console.print(
                f"[bold red]⚠️ Alerta: Se detectaron {len(alerts)} proyectos con entropía crítica:[/]"
            )
            for alert in alerts:
                console.print(
                    f"  - [bold]{alert['project']}[/]: {alert['message']} (Score: {alert['complexity_score']}/100)"
                )

        # Sugerencias si el monitor está deshabilitado
        if "entropy_alerts" not in status_dict:
            console.print(
                "[dim italic]Nota: El monitor de entropía podría no estar habilitado en la configuración.[/]"
            )
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        handle_cli_error(e, context="generating entropy report")
