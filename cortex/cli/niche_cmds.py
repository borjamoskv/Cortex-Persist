"""
CORTEX CLI — Niche Arbitrage Commands
"""

from __future__ import annotations

import asyncio

import click

from cortex.cli.common import console
from cortex.extensions.skills.niche_arbitrage.models import NicheTarget
from cortex.extensions.skills.niche_arbitrage.pipeline import NicheArbitrageEngine


@click.group(name="niche", help="Niche Arbitrage — Market Intelligence Pipeline")
def niche_cmds():
    """Domain intelligence and market anomaly arbitrage."""
    pass


@niche_cmds.command("extract", help="Run the extraction and synthesis pipeline on a target.")
@click.argument("url")
@click.option("--name", required=True, help="Semantic name of the target")
@click.option("--tags", default="", help="Comma separated tags")
@click.option("--output", "-o", default=None, help="Save report to file (Markdown)")
def extract_cmd(url: str, name: str, tags: str, output: str | None):
    """Executes the Niche Arbitrage ETL pipeline."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    target = NicheTarget(url=url, name=name, tags=tag_list)

    # We use asyncio.run to kick off the pipeline
    console.print(f"[bold cyan]▶ Iniciando Arbitraje de Nicho en:[/bold cyan] {name} ({url})")

    engine = NicheArbitrageEngine()

    with console.status("[bold yellow]Ingiriendo y Sintetizando Exergía...[/bold yellow]"):
        report = asyncio.run(engine.run_pipeline(target))

    md_content = report.to_markdown()

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(md_content)
        console.print(f"[bold green]✔ Reporte guardado en {output}[/bold green]")
    else:
        # Print directly to console via Rich Markdown if installed, else raw text
        from rich.markdown import Markdown

        console.print(Markdown(md_content))
