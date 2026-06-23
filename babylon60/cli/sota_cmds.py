# [C5-REAL] Exergy-Maximized
"""
SOTA Command-Line Interface.
Enables interaction with SOTA-Vector-Engine-Omega to find money in frontier technology.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from babylon60.cli.common import _run_async, cli, console, get_engine
from babylon60.engine.sota_vector_engine import SOTAVectorEngine


@click.group("sota")
def sota_cmds():
    """📈 SOTA: Sovereign Signal Intelligence & Commercial Moats."""
    pass

@sota_cmds.command("scan")
@click.option("--query", "-q", help="Filter signals by query term.")
def scan_cmd(query: str | None):
    """Scan the frontier for new intelligence and display candidate nodes."""
    console.print("[bold cyan]🚀 Scanning Frontier Channels (arXiv, GitHub, RFCs)...[/bold cyan]")
    
    engine = get_engine()
    sota = SOTAVectorEngine(engine=engine)
    
    signals = _run_async(sota.detect_signals(source_query=query))
    
    if not signals:
        console.print("[yellow]⚠ No signals detected matching the filter.[/yellow]")
        return
        
    table = Table(title="🤖 Detected Frontier Signals", show_lines=True)
    table.add_column("Domain/Subdomain", style="cyan", width=25)
    table.add_column("Title / Source", style="white")
    table.add_column("Claimed Benchmark Delta", style="green")
    
    for sig in signals:
        table.add_row(
            f"{sig['domain']}\n[dim]{sig['subdomain']}[/dim]",
            f"[bold]{sig['title']}[/bold]\n[dim]{sig['url']}[/dim]",
            sig["claimed_benchmarks"]
        )
        
    console.print(table)

@sota_cmds.command("verify")
@click.argument("repo_url")
def verify_cmd(repo_url: str):
    """Run diagnostic setup, dependency audit and check the hype index of a repo."""
    console.print(f"[bold cyan]🔍 Commencing Deep Verification for repo: {repo_url}...[/bold cyan]")
    
    engine = get_engine()
    sota = SOTAVectorEngine(engine=engine)
    
    report = _run_async(sota.verify_code(repo_url))
    
    panel_text = f"""[bold]Verification Status[/bold]: [green]{report['verification_status']}[/green]
[bold]Detected Dependencies[/bold]: {", ".join(report['dependencies_detected'])}
[bold]Verified Speedup / Throughput[/bold]: {report['benchmark_variance']}
[bold]Hype Factor (0-1)[/bold]: {report['hype_index']:.2f}
[bold]Production Readiness[/bold]: {report['production_readiness']}
[bold]Timestamp[/bold]: {report['run_timestamp']}"""
    
    console.print(Panel(
        panel_text,
        title="🔎 Code Audit Report",
        border_style="bright_blue",
        padding=(1, 2)
    ))

@sota_cmds.command("monetize")
@click.option("--title", required=True, help="Title of the research paper or signal.")
@click.option("--repo", required=True, help="GitHub repository URL.")
@click.option("--domain", default="AI", help="Domain (AI, Infra, Crypto, etc.).")
@click.option("--subdomain", default="Optimization", help="Specific technical subdomain.")
@click.option("--url", default="https://arxiv.org/abs/0000.0000", help="Arxiv or paper link.")
@click.option("--mechanism", required=True, help="Description of the technical mechanism.")
@click.option("--benchmarks", default="Under evaluation", help="Claimed performance delta.")
def monetize_cmd(title: str, repo: str, domain: str, subdomain: str, url: str, mechanism: str, benchmarks: str):
    """Convert raw research directly into a verified commercial opportunity and save to ledger."""
    console.print("[bold magenta]💸 Converting Technical Research into Moats & Revenue Opportunities...[/bold magenta]")
    
    engine = get_engine()
    sota = SOTAVectorEngine(engine=engine)
    
    input_data = {
        "title": title,
        "repo": repo,
        "domain": domain,
        "subdomain": subdomain,
        "url": url,
        "mechanism": mechanism,
        "claimed_benchmarks": benchmarks
    }
    
    opportunity = _run_async(sota.convert_research_to_opportunity(input_data))
    
    fn = opportunity["Frontier_Node"]
    bo = opportunity["Business_Opportunity"]
    
    console.print("\n[bold green]✔ Opportunity Processed & Persisted back to Cortex Ledger! Hash: C5-REAL[/bold green]")
    
    node_table = Table(title="📦 Emitted Frontier Node", show_lines=True)
    node_table.add_column("Field", style="cyan")
    node_table.add_column("Details", style="white")
    node_table.add_row("Title", fn["Title"])
    node_table.add_row("Impact (6-12m)", f"[bold green]{fn['Impact_Probability_6_12_Months']}[/bold green]")
    node_table.add_row("Confidence Level", fn["Confidence_Level"])
    node_table.add_row("Hype Index", f"{fn['Hype_Index']:.2f}")
    node_table.add_row("Verified Output", fn["Cortex_Verified_Throughput"])
    
    console.print(node_table)
    
    biz_table = Table(title="💼 Commercial Monetization Vector", show_lines=True)
    biz_table.add_column("Aspect", style="yellow")
    biz_table.add_column("Value Strategy", style="white")
    biz_table.add_row("Value Proposition", bo["Value_Proposition"])
    biz_table.add_row("Ideal Customer", bo["Ideal_Customer"])
    biz_table.add_row("Technical Risk", bo["Technical_Risk"])
    biz_table.add_row("Integration Cost", bo["Estimated_Integration_Cost"])
    
    console.print(biz_table)
    
    console.print("\n[dim]To generate commercial products (newsletter, memos), run: `cortex sota product`[/dim]")

@sota_cmds.command("product")
@click.option("--title", required=True, help="Title of the signal to build products for.")
@click.option("--type", "product_type", type=click.Choice(["newsletter", "vc_memo", "cto_roadmap"]), default="newsletter", help="Commercial product format.")
@click.option("--repo", default="https://github.com/example/repo", help="Associated Git Repo.")
def product_cmd(title: str, product_type: str, repo: str):
    """Forge a premium newsletter, VC investment memo, or CTO roadmap for a signal."""
    console.print(f"[bold cyan]🔨 Forging Product format '{product_type}' for '{title}'...[/bold cyan]")
    
    engine = get_engine()
    sota = SOTAVectorEngine(engine=engine)
    
    # 1. Fetch/mock signal details
    signal = {
        "title": title,
        "domain": "AI",
        "subdomain": "Inference Optimization",
        "url": "https://arxiv.org/abs/2402.17764",
        "repo": repo,
        "mechanism": "Quantized state cache serving and custom Triton matrix kernels.",
        "claimed_benchmarks": "4x reduced Serving memory layout."
    }
    
    # 2. Run mock pipeline sections to output product
    verification = _run_async(sota.verify_code(repo))
    impact = _run_async(sota.predict_impact(signal, verification))
    kmap = _run_async(sota.build_knowledge_map(signal))
    segments = _run_async(sota.segment_customers(signal, impact))
    actions = _run_async(sota.generate_recommended_actions(segments))
    
    product_markdown = _run_async(sota.forge_commercial_product(
        signal=signal,
        verification=verification,
        impact=impact,
        kmap=kmap,
        actions=actions,
        product_type=product_type
    ))
    
    console.print("\n--- PRODUCT OUTPUT START ---")
    console.print(product_markdown)
    console.print("--- PRODUCT OUTPUT END ---\n")
    console.print("[bold green]✔ Product successfully compiled to stdout.[/bold green]")

# Register the subcommands group back to click CLI bootstrap
cli.add_command(sota_cmds)
