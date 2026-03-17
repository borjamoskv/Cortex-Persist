from typing import Optional

"""AUTOROUTER-1 — CLI commands for CORTEX integration.

Commands:
  cortex autorouter start    → Arranca el daemon
  cortex autorouter stop     → Detiene el daemon
  cortex autorouter status   → Estado actual
  cortex autorouter history  → Historial de mutaciones
  cortex autorouter test     → Test rápido
  cortex autorouter config   → Genera config personalizable
  cortex autorouter enable-boot → Instala en launchd para auto-arranque
  cortex autorouter disable-boot→ Desinstala de launchd
  cortex autorouter logs     → Tail al log del daemon
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from cortex.cli.errors import err_execution_failed, err_platform_unsupported, err_skill_not_found
from cortex.core.paths import CORTEX_DIR

__all__ = [
    "CORTEX_DIR",
    "DAEMON_SCRIPT",
    "LOG_FILENAME",
    "LOG_PATH",
    "PLIST_NAME",
    "PLIST_PATH",
    "autorouter_cmds",
    "config",
    "disable_boot",
    "enable_boot",
    "history",
    "logs",
    "router_status",
    "start",
    "stop",
    "test",
]

console = Console()

DAEMON_SCRIPT = (
    Path.home()
    / ".gemini"
    / "antigravity"
    / "skills"
    / "autorouter-1"
    / "scripts"
    / "autorouter_daemon.py"
)

# Constants for file paths
LOG_FILENAME = "router_daemon.log"
LOG_PATH = CORTEX_DIR / LOG_FILENAME


def _run_daemon(args: list[str]) -> Optional[int]:
    """Ejecuta el daemon script con los argumentos dados.

    Returns:
        Exit code from the daemon process, or None if the daemon script
        was not found (error already reported via err_skill_not_found).
    """
    if not DAEMON_SCRIPT.exists():
        err_skill_not_found("AUTOROUTER-1", str(DAEMON_SCRIPT))
        return None
    try:
        result = subprocess.run(["python3", str(DAEMON_SCRIPT)] + args, check=False)
        return result.returncode
    except (OSError, ValueError, KeyError) as e:
        err_execution_failed(f"python3 {DAEMON_SCRIPT}", str(e))
        return None


@click.group(name="autorouter")
def autorouter_cmds():
    """⚡ AUTOROUTER-1 v3.0: Cognitive Switch Engine.

    Daemon soberano que muta el modelo de IA según el modo de operación.
    """
    pass


@autorouter_cmds.command()
@click.option("--background", "-bg", is_flag=True, help="Arrancar en background")
def start(background):
    """Arrancar el daemon de ruteo cognitivo."""
    if background:
        console.print("[bold cyan]🚀 Arrancando AUTOROUTER-1 en background...[/]")
        CORTEX_DIR.mkdir(parents=True, exist_ok=True)
        log_handle = LOG_PATH.open("a")  # Popen takes ownership; closed on process exit
        subprocess.Popen(
            ["python3", str(DAEMON_SCRIPT)],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        console.print(f"[green]✓[/] Daemon arrancado. Log: {LOG_PATH}")
    else:
        _run_daemon([])


@autorouter_cmds.command()
def stop():
    """Detener el daemon limpiamente."""
    code = _run_daemon(["--stop"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command(name="status")
def router_status():
    """Mostrar estado del daemon."""
    code = _run_daemon(["--status"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
@click.option("-n", default=20, help="Número de entradas a mostrar")
def history(n):
    """Ver historial de mutaciones cognitivas."""
    code = _run_daemon(["--history", str(n)])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
def test():
    """Test rápido de todas las funciones."""
    code = _run_daemon(["--test"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
def config():
    """Generar autorouter.config.json personalizable."""
    code = _run_daemon(["--init-config"])
    if code != 0:
        sys.exit(code)


PLIST_NAME = "com.moskv.autorouter.plist"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME


@autorouter_cmds.command(name="enable-boot")
def enable_boot():
    """Instala AUTOROUTER-1 en launchd para inicio automático en macOS."""
    if sys.platform != "darwin":
        err_platform_unsupported("launchd")

    python_path = sys.executable
    script_path = str(DAEMON_SCRIPT)
    log_path = str(LOG_PATH)
    user_id = subprocess.check_output(["id", "-u"], text=True).strip()

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.moskv.autorouter</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>"""

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content)

    console.print(f"[cyan]ℹ️ Creado plist en {PLIST_PATH}[/]")

    # Cargar en launchd usando bootstrap (moderno)
    try:
        # Intentar bootout previo (limpieza)
        subprocess.run(
            ["launchctl", "bootout", f"gui/{user_id}", str(PLIST_PATH)], capture_output=True
        )
        # Habilitar y bootstrap
        subprocess.run(
            ["launchctl", "enable", f"gui/{user_id}/com.moskv.autorouter"], capture_output=True
        )
        res = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{user_id}", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )

        if res.returncode == 0:
            console.print(
                "[bold green]✅ AUTOROUTER-1 instalado y arrancado vía launchd (bootstrap).[/]"
            )
        else:
            # Fallback a load si bootstrap falla (sistemas antiguos)
            res = subprocess.run(
                ["launchctl", "load", "-w", str(PLIST_PATH)], capture_output=True, text=True
            )
            if res.returncode == 0:
                console.print("[bold green]✅ AUTOROUTER-1 instalado vía legacy load.[/]")
            else:
                console.print(f"[bold red]❌ Error al cargar launchd:[/] {res.stderr}")
    except (OSError, subprocess.SubprocessError) as e:
        err_execution_failed("launchctl bootstrap", str(e))


@autorouter_cmds.command(name="disable-boot")
def disable_boot():
    """Desinstala AUTOROUTER-1 de launchd."""
    if sys.platform != "darwin":
        err_platform_unsupported("launchd")

    if not PLIST_PATH.exists():
        console.print("[yellow]⚠️ No hay configuración launchd instalada.[/]")
        return

    user_id = subprocess.check_output(["id", "-u"], text=True).strip()
    try:
        # Deshabilitar y bootout
        subprocess.run(
            ["launchctl", "disable", f"gui/{user_id}/com.moskv.autorouter"], capture_output=True
        )
        subprocess.run(
            ["launchctl", "bootout", f"gui/{user_id}", str(PLIST_PATH)], capture_output=True
        )
        # Fallback unload
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)

        PLIST_PATH.unlink(missing_ok=True)
        console.print("[bold green]✅ AUTOROUTER-1 desinstalado de launchd.[/]")
        _run_daemon(["--stop"])
    except (OSError, subprocess.SubprocessError) as e:
        err_execution_failed("launchctl bootout", str(e))


@autorouter_cmds.command()
def logs():
    """Sigue (tail) los logs del daemon en tiempo real."""
    if not LOG_PATH.exists():
        console.print(f"[yellow]⚠️ No se encontró log en {LOG_PATH}[/]")
        sys.exit(1)

    from cortex.extensions.platform.sys import tail_file_command

    console.print(f"[dim]Mostrando logs de: {LOG_PATH} (Ctrl+C para salir)[/]")
    try:
        subprocess.run(tail_file_command(str(LOG_PATH)))
    except KeyboardInterrupt:
        pass
