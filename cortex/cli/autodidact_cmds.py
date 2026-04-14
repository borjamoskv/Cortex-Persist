"""
CLI commands for Autodidact Omega (v4.0).
JIT AST Compilation and Thermodynamic Sovereign Forging.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.syntax import Syntax

from cortex.cli.common import _run_async, cli, console
from cortex.extensions.swarm.autodidact_actuator import autodidact_ingest


@cli.group(name="autodidact")
def autodidact_group() -> None:
    """Autodidact Omega: Sovereign Thermodynamic Crystal Forge."""
    pass


@autodidact_group.command(name="ingest")
@click.argument("source_file", type=click.Path(exists=True, dir_okay=False))
def ingest(source_file: str) -> None:
    """Ingest a Python file through the JIT Sovereign Sandbox."""
    console.print(f"[bold cyan]🔥 Autodidact-Ω Ingestion Initiated[/bold cyan] » '{source_file}'")

    with open(source_file) as f:
        source_code = f.read()

    async def _run_ingest():
        # expected_yield_gain > 0 forces a check inside the actuator
        return await autodidact_ingest(
            source_code, expected_yield_gain=1.0, metadata={"source": source_file}
        )

    result = _run_async(_run_ingest())

    if result.get("action") == "CRYSTALLIZE":
        console.print(
            f"[bold green]✓ JIT Forging Success[/bold green] (Resonance: {result.get('resonance', 0.0)})"
        )
        console.print(f"Elapsed Time: {result.get('yield_time_ms', 0.0):.2f}ms")
        console.print(f"Discovered State: {result.get('locals')}")
    else:
        console.print(f"[bold red]✗ Termodynamic Purge: {result.get('reason')}[/bold red]")
        console.print(f"Details: {result.get('details', result.get('yield', 'Unknown'))}")


@autodidact_group.command(name="jit")
@click.argument("code_snippet")
def jit_eval(code_snippet: str) -> None:
    """Directly evaluate a snippet of Python in the AST Sandbox."""
    console.print("[bold cyan]⚡ JIT Quick Eval[/bold cyan]")

    async def _run_ingest():
        return await autodidact_ingest(code_snippet, expected_yield_gain=1.0, metadata={})

    result = _run_async(_run_ingest())

    if result.get("action") == "CRYSTALLIZE":
        console.print(
            f"[bold green]✓ Success ({result.get('yield_time_ms', 0.0):.2f}ms)[/bold green]"
        )
        console.print(f"Locals Exergy: {result.get('locals')}")
    else:
        console.print(f"[bold red]✗ Purged: {result.get('reason')}[/bold red]")
        console.print(f"Details: {result.get('details', result.get('yield', 'Unknown'))}")


@autodidact_group.command(name="audit")
def audit():
    """Mide el impacto termodinámico de las inferencias previas usando crystal_thermometer.py."""
    from cortex.cli.common import get_engine
    from cortex.extensions.swarm.crystal_thermometer import scan_all_crystals

    console.print("[bold cyan]🔍 CORTEX: Autodidact-Ω Audit[/bold cyan]")
    engine = get_engine()

    async def _audit():
        from cortex.database.core import connect

        conn = connect(engine._db_path)
        return await scan_all_crystals(conn, project="autodidact_knowledge")

    vitals = _run_async(_audit())

    from rich.table import Table

    table = Table(title="💎 Yield Crystals Vitals (Thermodynamic Sync)")
    table.add_column("Fact ID", style="dim", width=20)
    table.add_column("Temperature", style="red")
    table.add_column("Resonance", style="green")
    table.add_column("Quadrant", style="cyan")
    table.add_column("Action", style="yellow")

    for v in vitals:
        table.add_row(
            v.fact_id[-8:],
            f"{v.temperature:.2f}",
            f"{v.resonance:.2f}",
            v.quadrant,
            v.recommendation,
        )

    console.print(table)


@autodidact_group.command(name="crawl")
@click.argument("url")
def crawl(url: str):
    """LIBRARIAN-1 ∪ DEMIURGE-OMEGA = Autopoiesis."""
    import urllib.request

    from cortex.extensions.evolution.demiurge import DemiurgeCompiler

    console.print(f"[bold cyan]🕸️ LIBRARIAN-1 Ingesting: {url}[/bold cyan]")
    try:
        if url.startswith("http"):
            with urllib.request.urlopen(url, timeout=10) as response:
                text = response.read().decode("utf-8")
        else:
            with open(url) as f:
                text = f.read()
    except Exception as e:
        console.print(f"[bold red]✗ LIBRARIAN Error:[/bold red] {e}")
        return

    console.print("[dim]Extraction complete. Generating JIT Skill via DEMIURGE...[/dim]")

    async def _crawl():
        demiurge = DemiurgeCompiler()
        prompt = f"Based on this ingested text: {text[:2000]}... Write a python snippet that extracts its core utility. Do not include async def execute_skill, just pure python."
        code = await demiurge.llm.complete(
            prompt, system="Return ONLY python code.", temperature=0.1
        )
        if not code:
            return {"status": "failed", "reason": "No code generated."}

        # Clean up Markdown
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()

        console.print(
            Panel(Syntax(code, "python", theme="monokai"), title="[cyan]DEMIURGE Synthesis[/cyan]")
        )

        return await autodidact_ingest(code, expected_yield_gain=1.0, metadata={"source": url})

    result = _run_async(_crawl())

    if result.get("action") == "CRYSTALLIZE":
        console.print(
            f"[bold green]✓ JIT Forging Success[/bold green] (Resonance: {result.get('resonance', 0.0)})"
        )
        console.print(f"Elapsed Time: {result.get('yield_time_ms', 0.0):.2f}ms")
    else:
        console.print(f"[bold red]✗ Termodynamic Purge: {result.get('reason')}[/bold red]")
        console.print(f"Details: {result.get('details', result.get('yield', 'Unknown'))}")
