# [C5-REAL] Exergy-Maximized
"""
cat_id: stress-test-legion
cat_type: script
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env from repo root so API keys are visible to the process
_repo_root = Path(__file__).parent.parent
load_dotenv(_repo_root / ".env", override=False)
load_dotenv(_repo_root / ".env.local", override=True)

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from babylon60.core import config
from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.extensions.swarm.centauro_engine import CentauroEngine

console = Console()

async def run_mission(
    engine: CentauroEngine, 
    mission_id: int, 
    formation: str, 
    semaphore: asyncio.Semaphore,
    progress: Progress,
    task_id
):
    """Executes a single mission through the CentauroEngine under a thermal semaphore limit."""
    async with semaphore:
        start_time = time.time()
        try:
            result = await engine.engage(mission=f"Stress test task {mission_id}", formation=formation)
            elapsed = time.time() - start_time
            status = result.get("status", "unknown")
            progress.update(task_id, advance=1)
            return status, elapsed
        except Exception:
            elapsed = time.time() - start_time
            progress.update(task_id, advance=1)
            return "error", elapsed


async def main():
    parser = argparse.ArgumentParser(description="LEGIØN-1 Stress Test (C5-REAL Enhanced)")
    parser.add_argument("--missions", type=int, default=10, help="Total number of missions to execute")
    parser.add_argument("--concurrency", type=int, default=5, help="Maximum concurrent missions (Thermal Limiter)")
    parser.add_argument("--formation", default="HYDRA", help="Tactical formation to deploy")
    parser.add_argument("--sim", action="store_true", help="Force C4-SIM mode (No LLM calls)")
    parser.add_argument("--provider", help="Primary LLM provider (default: read from config)")
    parser.add_argument("--model", help="Primary LLM model (default: read from config)")

    args = parser.parse_args()

    # Dynamic LLM Provider configuration from config singleton or CLI overrides
    primary_provider_name = args.provider or config.LLM_PROVIDER or "gemini"
    primary_model_name = args.model or config.LLM_MODEL or "gemini-2.5-flash"

    console.print("[bold blue]🔱 LEGIØN-1 STRESS TEST ACTIVATED[/bold blue]")
    console.print(f"[cyan]MISSIONS:[/cyan] {args.missions}")
    console.print(f"[cyan]CONCURRENCY THRESHOLD:[/cyan] {args.concurrency}")
    console.print(f"[cyan]FORMATION:[/cyan] {args.formation}")
    console.print(f"[cyan]PRIMARY PROVIDER:[/cyan] {primary_provider_name}")
    console.print(f"[cyan]PRIMARY MODEL:[/cyan] {primary_model_name}")
    console.print(f"[cyan]MODE:[/cyan] {'[bold yellow]C4-SIM[/bold yellow]' if args.sim else '[bold red]C5-REAL[/bold red]'}")
    console.print()

    if not args.sim:
        from babylon60.extensions.llm.provider import LLMProvider
        primary_provider = LLMProvider(provider=primary_provider_name, model=primary_model_name)
        fallback_providers = [
            LLMProvider("cerebras"),
            LLMProvider("openrouter"),
            LLMProvider("ollama"),
        ]
        router = CortexLLMRouter(primary=primary_provider, fallbacks=fallback_providers)
    else:
        router = None

    # Instantiate the swarm engine
    engine = CentauroEngine(tolerance=0.67, router=router)
    semaphore = asyncio.Semaphore(args.concurrency)
    
    results = []
    start_time = time.time()

    # Isomorphic mapping to UI: Track execution state via rich progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Executing Swarm Missions...", total=args.missions)
        
        tasks = [
            run_mission(engine, i, args.formation, semaphore, progress, task_id)
            for i in range(1, args.missions + 1)
        ]
        
        results = await asyncio.gather(*tasks)

    total_elapsed = time.time() - start_time
    statuses = [r[0] for r in results]
    successes = statuses.count("success")
    errors = statuses.count("error")

    # Generate YAML Structural Proof (Rule R2)
    yaml_proof = f"""
Claim: Stress test execution structural invariant
Proof:
  Base:
    Missions: {args.missions}
    Concurrency: {args.concurrency}
    TimeElapsed: {total_elapsed:.2f}s
    Mode: {'C4-SIM' if args.sim else 'C5-REAL'}
  Range:
    Success: {successes}
    Failed: {errors}
  Confidence: C5-REAL
"""
    console.print(yaml_proof, style="bold green")

    # Render empirical data visually
    table = Table(title="Execution Matrix")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Time", f"{total_elapsed:.2f}s")
    table.add_row("Throughput", f"{(args.missions / total_elapsed):.2f} ops/s" if total_elapsed > 0 else "∞ ops/s")
    table.add_row("Success Rate", f"{(successes / args.missions) * 100:.1f}%")
    
    console.print(table)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
