# [C5-REAL] Exergy-Maximized
"""
NOUS Commands
CLI entry points for compiling, dry-running, and executing declarative .nous migrations.
"""

from pathlib import Path

import click

from cortex.cli.common import _run_async, cli, console, get_engine
from cortex.extensions.nous.compiler_v2 import NousCompilerV2
from cortex.extensions.nous.runtime import NousRuntime


@cli.group("nous")
def nous():
    """NOUS Database Migrator and AST Compiler."""
    pass


@nous.command("compile")
@click.argument("manifest_path", type=click.Path(exists=True, path_type=Path))
def compile_cmd(manifest_path: Path):
    """Compile a .nous manifest into a typed AST and display it."""
    console.print(f"[bold cyan]🧠 Compiling NOUS manifest: {manifest_path}[/bold cyan]")

    with open(manifest_path, encoding="utf-8") as f:
        manifest_text = f.read()

    compiler = NousCompilerV2()

    with console.status("[cyan]Invoking LLM structured compilation...[/cyan]"):
        ast = _run_async(compiler.compile(manifest_text))

    console.print("[bold green]✔ AST Compiled Successfully[/bold green]")
    console.print(ast.model_dump_json(indent=2))


@nous.command("dry-run")
@click.argument("manifest_path", type=click.Path(exists=True, path_type=Path))
def dry_run_cmd(manifest_path: Path):
    """Simulate a .nous migration without side-effects."""
    console.print(f"[bold cyan]🛡️ Running NOUS dry-run for: {manifest_path}[/bold cyan]")

    with open(manifest_path, encoding="utf-8") as f:
        manifest_text = f.read()

    compiler = NousCompilerV2()

    with console.status("[cyan]Compiling manifest...[/cyan]"):
        ast = _run_async(compiler.compile(manifest_text))

    engine = get_engine()
    runtime = NousRuntime(engine)

    with console.status("[cyan]Simulating operations...[/cyan]"):
        result = _run_async(runtime.dry_run(ast))

    if result.ok:
        console.print("[bold green]✔ Dry-Run Passed[/bold green]")
    else:
        console.print("[bold red]❌ Dry-Run Failed or yielded warnings[/bold red]")

    console.print(result.model_dump_json(indent=2))


@nous.command("execute")
@click.argument("manifest_path", type=click.Path(exists=True, path_type=Path))
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def execute_cmd(manifest_path: Path, yes: bool):
    """Execute a .nous migration directly against the active CORTEX engine."""
    console.print(f"[bold magenta]⚠️ EXECUTING REAL MIGRATION: {manifest_path}[/bold magenta]")

    if not yes:
        click.confirm("Are you sure you want to apply this migration?", abort=True)

    with open(manifest_path, encoding="utf-8") as f:
        manifest_text = f.read()

    compiler = NousCompilerV2()

    with console.status("[cyan]Compiling manifest...[/cyan]"):
        ast = _run_async(compiler.compile(manifest_text))

    engine = get_engine()
    runtime = NousRuntime(engine)

    with console.status("[cyan]Executing AST operations...[/cyan]"):
        _run_async(runtime.execute(ast))

    console.print("[bold green]✔ Migration applied successfully to C5-REAL.[/bold green]")
