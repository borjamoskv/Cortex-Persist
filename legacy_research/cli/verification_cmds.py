# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from legacy_research.cli.common import cli
from legacy_research.verification.verifier import SovereignVerifier

console = Console()


@cli.command("verify-files")
@click.argument("files", nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=False))
def verify_files_cmd(files: tuple[str, ...]) -> None:
    """Verifica archivos Python contra los invariantes de seguridad soberanos."""
    if not files:
        console.print("[yellow]No se especificaron archivos para verificar.[/]")
        return

    verifier = SovereignVerifier()
    all_valid = True

    table = Table(
        title="Resultados de Verificación Formal (Z3 + AST)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Archivo", style="cyan")
    table.add_column("Resultado", style="bold")
    table.add_column("Detalles de Violación", style="red")

    for file_path in files:
        if not file_path.endswith(".py"):
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()

            result = verifier.check(code, {"file_path": file_path})
            if result.is_valid:
                table.add_row(file_path, "[green]PASSED[/]", "[dim]Zero violations[/]")
            else:
                all_valid = False
                violations_str = "\n".join(
                    [f"- [{v['id']}] {v['message']}" for v in result.violations]
                )
                table.add_row(file_path, "[red]FAILED[/]", violations_str)
        except Exception as e:
            all_valid = False
            table.add_row(file_path, "[red]CRASHED[/]", f"Error de lectura/procesamiento: {str(e)}")

    console.print(table)

    if not all_valid:
        console.print("\n[bold red]❌ FALLÓ LA VERIFICACIÓN FORMAL. Bloqueando integración.[/]")
        raise click.exceptions.Exit(1)

    console.print("\n[bold green]✓ VERIFICACIÓN FORMAL COMPLETADA CON ÉXITO.[/]")
