from pathlib import Path

import click

from babylon60.cli.common import cli
from babylon60.engine.auto_instrumentor import instrument_directory


@cli.command("instrument")
@click.option("--path", "-p", required=True, type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), help="Directory to auto-instrument.")
@click.option("--dry-run", is_flag=True, help="Do not modify files, just show what would be done.")
def instrument_cmd(path: Path, dry_run: bool):
    """
    [C5-REAL] Auto-Instrument Enterprise Repositories.
    
    Scans the given path for Python files and injects the CORTEX MTK/Trace
    decorator into functions containing LLM patterns.
    """
    click.secho("=== [C5-REAL] Enterprise Auto-Instrumentor ===", fg="cyan", bold=True)
    click.secho(f"Targeting: {path}", fg="cyan")
    
    files_modified, hooks_injected = instrument_directory(path, dry_run)
    
    click.secho("\n=== SUMMARY ===", fg="cyan", bold=True)
    if dry_run:
        click.secho(f"[DRY RUN] Would modify {files_modified} files and inject {hooks_injected} CORTEX guards.", fg="yellow")
    else:
        click.secho(f"[+] Modified {files_modified} files.", fg="green")
        click.secho(f"[+] Injected {hooks_injected} CORTEX guards.", fg="green")
        click.secho("Contención Epistémica Establecida.", fg="green", bold=True)
