"""SCRAPER-Ω CLI — Sovereign Web Extraction commands.

Commands:
    cortex scraper scrape <URL>   — Extract a single URL
    cortex scraper batch <FILE>   — Batch extract from URL file
    cortex scraper map <URL>      — Discover site URLs
"""

from __future__ import annotations
from typing import Optional

import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def scraper():
    """SCRAPER-Ω: Sovereign Web Extraction Engine."""
    pass


@scraper.command()
@click.argument("url")
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["auto", "http_fast", "jina", "firecrawl", "playwright"]),
    default="auto",
    help="Extraction strategy.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Output format.",
)
@click.option("--no-robots", is_flag=True, default=False, help="Skip robots.txt check.")
@click.option("--persist", is_flag=True, default=False, help="Persist result to CORTEX ledger.")
def scrape(
    url: str,
    strategy: str,
    output: Optional[str],
    output_format: str,
    no_robots: bool,
    persist: bool,
):
    """Extract content from a single URL."""
    from cortex.cli.common import _run_async
    from cortex.extensions.scraper.engine import ScraperEngine
    from cortex.extensions.scraper.models import ExtractionStrategy, ScrapeRequest

    console.print(
        Panel(
            f"[bold cyan]🕷️ SCRAPER-Ω[/bold cyan]: {url}",
            subtitle=f"strategy={strategy}",
            border_style="bright_green",
        )
    )

    request = ScrapeRequest(
        url=url,
        strategy=ExtractionStrategy(strategy),
        respect_robots=not no_robots,
    )

    engine = ScraperEngine()
    result = _run_async(engine.scrape(request))

    if result.status == "error":
        console.print(f"[bold red]❌ Error:[/bold red] {result.error}")
        raise SystemExit(1)

    # Display result
    console.print(f"\n[bold green]✅ Extracted:[/bold green] {result.title or 'Untitled'}")
    console.print(
        f"[dim]Strategy: {result.strategy_used.value} | "
        f"Time: {result.elapsed_ms:.0f}ms | "
        f"Hash: {result.content_hash}[/dim]"
    )

    if output_format == "json":
        payload = {
            "url": result.url,
            "title": result.title,
            "content": result.content,
            "hash": result.content_hash,
            "strategy": result.strategy_used.value,
            "elapsed_ms": result.elapsed_ms,
        }
        text = json.dumps(payload, indent=2)
    else:
        text = result.content

    if output:
        with open(output, "w") as f:
            f.write(text)
        console.print(f"[dim]Written to {output}[/dim]")
    else:
        # Show preview (first 500 chars)
        preview = text[:500] + ("..." if len(text) > 500 else "")
        console.print(Panel(preview, title="Content Preview", border_style="dim"))

    if persist:
        _persist_to_cortex(result)

    console.print(
        f"\n[bold cyan]🕷️ EXTRACTED:[/bold cyan] 1 page | "
        f"source={result.url} | "
        f"size={len(result.content)} chars"
    )


@scraper.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["auto", "http_fast", "jina", "firecrawl", "playwright"]),
    default="auto",
    help="Extraction strategy.",
)
@click.option("--concurrency", "-c", type=int, default=3, help="Max concurrent requests.")
@click.option("--rate-limit", "-r", type=float, default=1.0, help="Requests per second.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output directory.")
def batch(
    file: str,
    strategy: str,
    concurrency: int,
    rate_limit: float,
    output: Optional[str],
):
    """Batch extract URLs from a newline-delimited file."""
    from cortex.cli.common import _run_async
    from cortex.extensions.scraper.engine import ScraperEngine
    from cortex.extensions.scraper.models import ExtractionStrategy

    with open(file) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    console.print(
        Panel(
            f"[bold cyan]📦 BATCH SCRAPE[/bold cyan]: {len(urls)} URLs",
            subtitle=f"concurrency={concurrency} | rate={rate_limit} req/s",
            border_style="bright_green",
        )
    )

    engine = ScraperEngine()
    job = _run_async(
        engine.batch_scrape(
            urls=urls,
            strategy=ExtractionStrategy(strategy),
            concurrency=concurrency,
            rate_limit=rate_limit,
        )
    )

    # Results table
    table = Table(title=f"Job {job.job_id} Results")
    table.add_column("URL", style="cyan", max_width=50)
    table.add_column("Status", style="green")
    table.add_column("Strategy", style="yellow")
    table.add_column("Time (ms)", justify="right")

    for r in job.results:
        status = "✅" if r.status == "success" else f"❌ {r.error or ''}"
        table.add_row(r.url[:50], status, r.strategy_used.value, f"{r.elapsed_ms:.0f}")

    console.print(table)

    if output:
        import os

        os.makedirs(output, exist_ok=True)
        for _i, r in enumerate(job.results):
            if r.status == "success":
                safe_name = r.url.replace("https://", "").replace("http://", "")
                safe_name = safe_name.replace("/", "_")[:80]
                filepath = os.path.join(output, f"{safe_name}.md")
                with open(filepath, "w") as f:
                    f.write(f"# {r.title}\n\n{r.content}")

    console.print(
        f"\n[bold cyan]📦 BATCH COMPLETE:[/bold cyan] "
        f"{job.successful_count}/{len(urls)} successful | "
        f"{job.error_count} errors"
    )


@scraper.command(name="map")
@click.argument("url")
@click.option("--depth", "-d", type=int, default=2, help="Max crawl depth.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file for URLs.")
def map_site(url: str, depth: int, output: Optional[str]):
    """Discover URLs from a website (sitemap)."""
    from cortex.cli.common import _run_async
    from cortex.extensions.scraper.engine import ScraperEngine

    console.print(
        Panel(
            f"[bold cyan]🗺️ SITE MAP[/bold cyan]: {url}",
            subtitle=f"depth={depth}",
            border_style="bright_green",
        )
    )

    engine = ScraperEngine()
    urls = _run_async(engine.map_site(url, max_depth=depth))

    for u in urls:
        console.print(f"  [dim]→[/dim] {u}")

    if output:
        with open(output, "w") as f:
            f.write("\n".join(urls))
        console.print(f"\n[dim]Written {len(urls)} URLs to {output}[/dim]")

    console.print(f"\n[bold cyan]🗺️ MAPPED:[/bold cyan] {len(urls)} URLs discovered")


def _persist_to_cortex(result) -> None:
    """Persist a ScrapeResult to the CORTEX ledger."""
    try:
        from cortex.cli.common import _run_async, get_engine

        engine = get_engine()
        _run_async(
            engine.store(
                project="scraping",
                content=f"Scraped: {result.url} — {result.title}",
                fact_type="bridge",
                tags=["scraper", "web_extraction", result.strategy_used.value],
                confidence="C4",
                source="agent:scraper-omega",
                meta={
                    "url": result.url,
                    "hash": result.content_hash,
                    "strategy": result.strategy_used.value,
                    "elapsed_ms": result.elapsed_ms,
                    "content_length": len(result.content),
                },
            )
        )
        console.print("[dim green]💎 Persisted to CORTEX Ledger[/dim green]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[dim red]⚠️ CORTEX persist failed: {e}[/dim red]")
