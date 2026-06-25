# [C5-REAL] Exergy-Maximized
"""
Frontier CLI Commands
Control the R&D and Metabolism pulse of CORTEX.
"""

import asyncio

import click
from rich.table import Table

from cortex.cli.common import cli, console, get_engine
from legacy_research.extensions.daemon.frontier import FrontierDaemon


@click.group("frontier")
def frontier_cmds():
    """🚀 Frontier: Sovereign Evolution & Metabolism."""


cli.add_command(frontier_cmds)


@frontier_cmds.command("scan")
@click.option("--source", "-s", help="Specific URL or domain to ingest.")
def scan_cmd(source: str | None):
    """Scan the frontier for new intelligence (Cognitive Ingestion)."""
    console.print("[bold cyan]🚀 Starting Frontier Scan...[/bold cyan]")
    engine = get_engine()
    daemon = FrontierDaemon(engine=engine)

    if source:
        console.print(f"Ingesting source: [yellow]{source}[/yellow]")
        asyncio.run(daemon._run_ingestion())
    else:
        asyncio.run(daemon._run_ingestion())

    console.print("[bold green]✔ Ingestion cycle complete.[/bold green]")


@frontier_cmds.command("metabolize")
@click.option("--target", "-t", help="Target file or directory to metabolize.")
@click.option("--commit/--dry-run", default=False, help="Allow commits if entropy gate passes.")
def metabolize_cmd(target: str | None, commit: bool):
    """Force a metabolism cycle (Ouroboros-Omega) on target."""
    console.print("[bold magenta]♾️  Initializing Forced Metabolism Cycle...[/bold magenta]")
    engine = get_engine()
    daemon = FrontierDaemon(engine=engine, allow_commits=commit)

    asyncio.run(daemon._run_metabolism())

    mode = "COMMIT" if commit else "DRY-RUN"
    console.print(f"[bold green]✔ Metabolism cycle finished in {mode} mode.[/bold green]")


@frontier_cmds.command("intel-scan")
@click.option("--source", "-s", required=True, help="URL of the paper, repository, or website to scan.")
def intel_scan_cmd(source: str):
    """Scan a technical source using SOTA Vector Engine to extract pre-consensus signals."""
    console.print(f"[bold cyan]🔍 Scanning technical source for frontier signals:[/bold cyan] {source}")
    engine = get_engine()
    
    from legacy_research.extensions.frontier_intel.analyzer import FrontierIntelSystem
    system = FrontierIntelSystem(engine=engine)
    
    signals = asyncio.run(system.scan_source(source))
    
    if not signals:
        console.print("[bold yellow]⚠ No new C5-REAL-compliant frontier signals detected.[/bold yellow]")
        return
        
    _print_signals_table(signals)


@frontier_cmds.command("signals")
@click.option("--phase", "-p", type=click.Choice(["pre-consensus", "emerging", "consensus"]), help="Filter by consensus phase.")
@click.option("--min-novelty", "-n", type=float, default=0.0, help="Minimum novelty index (0.0 to 1.0).")
@click.option("--limit", "-l", type=int, default=10, help="Max number of signals to display.")
def signals_cmd(phase: str | None, min_novelty: float, limit: int):
    """Query and display detected frontier signals from CORTEX database."""
    console.print("[bold cyan]📊 Querying frontier signals database...[/bold cyan]")
    engine = get_engine()
    
    from legacy_research.extensions.frontier_intel.analyzer import FrontierIntelSystem
    system = FrontierIntelSystem(engine=engine)
    
    signals = asyncio.run(system.get_signals(phase=phase, min_novelty=min_novelty, top_k=limit))
    
    if not signals:
        console.print("[yellow]No matching frontier signals found in database.[/yellow]")
        return
        
    table = Table(title="Sovereign SOTA Vector Signals", title_style="bold green")
    table.add_column("Phase", style="cyan")
    table.add_column("Domain/Subdomain", style="magenta")
    table.add_column("Core Insight", style="white")
    table.add_column("Novelty", style="yellow", justify="right")
    table.add_column("Consensus", style="green", justify="right")
    
    for s in signals:
        phase_str = s.get("consensus_phase", "unknown").upper()
        # Color phase based on type
        if "pre-consensus" in phase_str.lower():
            phase_disp = f"[bold red]{phase_str}[/bold red]"
        elif "emerging" in phase_disp.lower() if "phase_disp" in locals() else "emerging" in phase_str.lower():
            phase_disp = f"[bold yellow]{phase_str}[/bold yellow]"
        else:
            phase_disp = f"[bold green]{phase_str}[/bold green]"
            
        table.add_row(
            phase_disp,
            f"{s.get('domain')}/{s.get('subdomain')}",
            s.get("core_insight")[:75] + "..." if len(s.get("core_insight", "")) > 75 else s.get("core_insight"), # type: ignore
            f"{s.get('novelty_index'):.3f}",
            f"{s.get('consensus_score'):.3f}"
        )
        
    console.print(table)


@frontier_cmds.command("analyze")
@click.option("--text", "-t", help="Raw text to analyze.")
@click.option("--file", "-f", type=click.Path(exists=True), help="Path to a text file to analyze.")
@click.option("--source-url", default="custom_input", help="Attribution URL for the source.")
def analyze_cmd(text: str | None, file: str | None, source_url: str):
    """Analyze raw technical text directly for frontier signals."""
    if not text and not file:
        raise click.UsageError("Either --text or --file must be provided.")
        
    if file:
        with open(file, encoding="utf-8") as f:
            content = f.read()
    else:
        content = text or ""
        
    console.print("[bold cyan]🧠 Analyzing raw technical text...[/bold cyan]")
    engine = get_engine()
    
    from legacy_research.extensions.frontier_intel.analyzer import FrontierIntelSystem
    system = FrontierIntelSystem(engine=engine)
    
    signals = asyncio.run(system.analyze_text(content, source_url=source_url))
    
    if not signals:
        console.print("[bold yellow]⚠ No frontier signals extracted or verified.[/bold yellow]")
        return
        
    _print_signals_table(signals)


def _print_signals_table(signals: list[dict]):
    """Helper to print a beautiful table of signals."""
    table = Table(title="Extracted Frontier Signals", title_style="bold green")
    table.add_column("Phase", style="cyan")
    table.add_column("Domain/Subdomain", style="magenta")
    table.add_column("Core Insight", style="white")
    table.add_column("Novelty", style="yellow")
    table.add_column("Repro", style="green")
    
    for s in signals:
        phase_str = s.get("consensus_phase", "unknown").upper()
        if "pre-consensus" in phase_str.lower():
            phase_disp = f"[bold red]{phase_str}[/bold red]"
        elif "emerging" in phase_str.lower():
            phase_disp = f"[bold yellow]{phase_str}[/bold yellow]"
        else:
            phase_disp = f"[bold green]{phase_str}[/bold green]"
            
        repro = s.get("Evidence", [{}])[0].get("Reproducible_Artifact", "unknown").upper()
        
        table.add_row(
            phase_disp,
            f"{s.get('Domain')}/{s.get('Subdomain')}",
            s.get("Core_Insight"),
            f"{s.get('novelty_index'):.3f}",
            repro
        )
        
    console.print(table)

