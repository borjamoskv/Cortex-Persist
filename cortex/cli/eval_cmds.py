"""V8 Governance: Measurement CLI."""

import click

from cortex.cli.common import DEFAULT_DB, cli, close_engine_sync, console, get_engine


@cli.command("eval")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--limit", default=20, help="Number of facts to evaluate")
@click.option("--top-k", default=5, help="Top K results to consider for recall")
def eval_cmd(db: str, limit: int, top_k: int) -> None:
    """Run V8 Recall Precision Proxy tests."""
    from cortex.memory.evaluator import calculate_recall_precision
    
    console.print("[bold cyan]🔬 CORTEX v8 Evaluation Engine[/]")
    console.print(f"Running Recall@{top_k} tests across {limit} samples...\n")
    
    engine = None
    try:
        engine = get_engine(db)
        result = calculate_recall_precision(engine, limit=limit, top_k=top_k)
        
        recall = result["recall_at_k"] * 100
        color = "green" if recall >= 80 else "yellow" if recall >= 50 else "red"
        
        console.print(f"Total Evaluated: {result['total']}")
        console.print(f"Semantic Hits: [green]{result['hits']}[/]")
        console.print(f"Recall@{top_k}: [{color}]{recall:.2f}%[/]")
        
        if recall == 0:
            console.print("\n[yellow]⚠️ Zero recall detected. Ensure L2 sqlite-vec is active and populated.[/]")
    finally:
        if engine:
            close_engine_sync(engine)
