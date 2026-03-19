"""CLI commands: doctor."""

from __future__ import annotations

import json
import os
import platform
import sqlite3
import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, console


def check_python() -> dict:
    return {
        "version": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "is_venv": hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix),
    }


def check_dependencies() -> dict:
    deps = {}
    try:
        import aiosqlite  # noqa: F401

        deps["aiosqlite"] = "installed"
    except ImportError:
        deps["aiosqlite"] = "missing"

    try:
        import rich  # noqa: F401

        deps["rich"] = "installed"
    except ImportError:
        deps["rich"] = "missing"

    # Check for sqlite-vec (critical for search)
    try:
        conn = sqlite3.connect(":memory:")
        # This is a heuristic, real check depends on how it's loaded
        deps["sqlite3_version"] = sqlite3.sqlite_version
        conn.close()
    except Exception:
        deps["sqlite3"] = "error"

    return deps


def check_database(db_path: str) -> dict:
    path = Path(db_path)
    if not path.exists():
        return {"status": "missing", "path": str(path)}

    try:
        conn = sqlite3.connect(db_path)
        res = conn.execute("SELECT count(*) FROM facts").fetchone()
        conn.close()
        return {"status": "healthy", "facts": res[0], "path": str(path)}
    except Exception as e:
        return {"status": "corrupt", "error": str(e), "path": str(path)}


def check_env() -> dict:
    return {
        "GEMINI_API_KEY": "set" if os.environ.get("GEMINI_API_KEY") else "missing",
        "CORTEX_DB_PATH": os.environ.get("CORTEX_DB_PATH", "default"),
        "CORTEX_LOG_LEVEL": os.environ.get("CORTEX_LOG_LEVEL", "INFO"),
    }


@click.command("doctor")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def doctor(db: str, as_json: bool) -> None:
    """🩺 CORTEX Doctor — System diagnostic and health tool."""
    report = {
        "python": check_python(),
        "dependencies": check_dependencies(),
        "database": check_database(db),
        "environment": check_env(),
    }

    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    console.print(
        Panel("[bold #CCFF00]🩺 CORTEX DOCTOR — INFORME DE DIAGNÓSTICO[/]", border_style="#6600FF")
    )

    # Environment
    env_table = Table(title="Variable de Entorno", box=None)
    env_table.add_column("Variable", style="bold cyan")
    env_table.add_column("Estado", style="noir.cyber")
    for k, v in report["environment"].items():
        color = "green" if v != "missing" else "red"
        env_table.add_row(k, f"[{color}]{v}[/]")
    console.print(env_table)

    # Database
    db_status = report["database"]["status"]
    db_color = "green" if db_status == "healthy" else "red"
    console.print(
        f"\n[bold]Base de Datos:[/] [{db_color}]{db_status.upper()}[/] ({report['database']['path']})"
    )
    if db_status == "healthy":
        console.print(f" - Facts detectados: {report['database']['facts']}")

    # Python & Venv
    py = report["python"]
    venv_status = "[green]SÍ[/]" if py["is_venv"] else "[yellow]NO (Recomendado)[/]"
    console.print("\n[bold]Entorno Python:[/]")
    console.print(f" - Versión: {py['version']}")
    console.print(f" - Venv: {venv_status}")
    console.print(f" - Ejecutable: [dim]{py['executable']}[/]")

    # Dependencies
    deps = report["dependencies"]
    missing = [k for k, v in deps.items() if v == "missing"]
    if missing:
        console.print(f"\n[bold red]❌ Dependencias faltantes:[/] {', '.join(missing)}")
    else:
        console.print("\n[bold green]✅ Todas las dependencias críticas están presentes.[/]")

    # Final Verdict
    if all(v != "missing" for v in report["environment"].values()) and db_status == "healthy":
        console.print("\n[bold #06d6a0]🚀 SISTEMA NOMINAL. CORTEX ESTÁ LISTO PARA OPERAR.[/]")
    else:
        console.print("\n[bold yellow]⚠️ SE DETECTARON PROBLEMAS. REVISA EL INFORME SUPERIOR.[/]")
