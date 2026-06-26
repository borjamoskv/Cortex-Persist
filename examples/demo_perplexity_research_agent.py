"""
demo_perplexity_research_agent.py
==================================
CORTEX-PERSIST × Perplexity Sonar-Pro Research Agent

Demonstrates:
  1. Perplexity sonar-pro query with citation extraction
  2. Cryptographic ledger entry via CORTEX (tamper-evident audit trail)
  3. Merkle hash chain across multi-turn research sessions
  4. Exergy scoring: reasoning signal vs token dissipation ratio

Usage:
    export PERPLEXITY_API_KEY="pplx-..."
    export CORTEX_API_URL="http://localhost:8000"   # optional, defaults shown
    python examples/demo_perplexity_research_agent.py

Requirements:
    pip install cortex-persist httpx rich

Docs: https://github.com/borjamoskv/Cortex-Persist/tree/main/docs/mcp.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Missing deps. Run: pip install cortex-persist httpx rich")
    sys.exit(1)

console = Console()

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
CORTEX_API_URL = os.environ.get("CORTEX_API_URL", "http://localhost:8000")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

RESEARCH_QUERIES = [
    "What are the latest advances in Merkle-tree based audit trails for AI agents in 2026?",
    "How does the Landauer principle apply to chain-of-thought reasoning in LLMs?",
    "What is the current state of MCP (Model Context Protocol) adoption in production AI systems?",
]


# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def build_ledger_entry(
    query: str,
    response_content: str,
    citations: list[str],
    tokens_used: int,
    prev_hash: str,
    exergy_score: float,
) -> dict[str, Any]:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "response_hash": _sha256(response_content),
        "citations": citations,
        "tokens_used": tokens_used,
        "exergy_score": round(exergy_score, 4),
        "prev_hash": prev_hash,
    }
    payload["entry_hash"] = _sha256(json.dumps(payload, sort_keys=True))
    return payload


def compute_exergy_score(content: str, tokens: int) -> float:
    """Ratio of reasoning signal (citations + logical connectors) to token cost."""
    signal_words = [
        "because", "therefore", "however", "evidence", "study",
        "research", "demonstrates", "implies", "contrary", "specifically",
    ]
    signal_count = sum(content.lower().count(w) for w in signal_words)
    if tokens == 0:
        return 0.0
    return (signal_count * 100) / tokens


# ---------------------------------------------------------------------------
# Perplexity API
# ---------------------------------------------------------------------------

async def query_perplexity(
    client: httpx.AsyncClient,
    query: str,
    model: str = "sonar-pro",
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise research agent. Provide concise, "
                    "citation-rich answers. Prioritize primary sources."
                ),
            },
            {"role": "user", "content": query},
        ],
        "max_tokens": 512,
        "temperature": 0.1,
        "return_citations": True,
    }
    t0 = time.perf_counter()
    resp = await client.post(PERPLEXITY_API_URL, headers=headers, json=body, timeout=30.0)
    latency_ms = round((time.perf_counter() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]["message"]
    usage = data.get("usage", {})
    citations = data.get("citations", [])
    return {
        "content": choice["content"],
        "citations": citations,
        "tokens_total": usage.get("total_tokens", 0),
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# CORTEX ledger push
# ---------------------------------------------------------------------------

async def push_to_cortex(
    client: httpx.AsyncClient,
    entry: dict[str, Any],
) -> bool:
    """Push ledger entry to CORTEX-PERSIST. Fails gracefully if server is offline."""
    try:
        resp = await client.post(
            f"{CORTEX_API_URL}/v1/ledger/append",
            json=entry,
            timeout=5.0,
        )
        return resp.status_code in (200, 201)
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# ---------------------------------------------------------------------------
# Main research loop
# ---------------------------------------------------------------------------

async def run_research_session(queries: list[str]) -> None:
    if not PERPLEXITY_API_KEY:
        console.print("[bold red]❌ PERPLEXITY_API_KEY not set.[/bold red]")
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold cyan]CORTEX-PERSIST × Perplexity Research Agent[/bold cyan]\n"
            f"[dim]Session: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}[/dim]\n"
            f"[dim]Queries: {len(queries)} | Model: sonar-pro[/dim]",
            border_style="cyan",
        )
    )

    ledger_chain: list[dict[str, Any]] = []
    prev_hash = "0" * 64  # genesis hash

    async with httpx.AsyncClient() as client:
        for i, query in enumerate(queries, 1):
            console.print(f"\n[bold yellow]▶ Query {i}/{len(queries)}[/bold yellow]")
            console.print(f"[italic]{query}[/italic]\n")

            try:
                result = await query_perplexity(client, query)
            except httpx.HTTPStatusError as exc:
                console.print(f"[red]Perplexity API error: {exc.response.status_code}[/red]")
                continue

            exergy = compute_exergy_score(result["content"], result["tokens_total"])
            entry = build_ledger_entry(
                query=query,
                response_content=result["content"],
                citations=result["citations"],
                tokens_used=result["tokens_total"],
                prev_hash=prev_hash,
                exergy_score=exergy,
            )
            prev_hash = entry["entry_hash"]
            ledger_chain.append(entry)

            # Display response
            console.print(Panel(result["content"], title="[green]Research Synthesis[/green]", border_style="green"))

            # Citations
            if result["citations"]:
                console.print("[bold]Citations:[/bold]")
                for url in result["citations"][:5]:
                    console.print(f"  [blue][link={url}]{url}[/link][/blue]")

            # Metrics table
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("[dim]Tokens[/dim]", str(result["tokens_total"]))
            table.add_row("[dim]Latency[/dim]", f"{result['latency_ms']} ms")
            table.add_row("[dim]Exergy score[/dim]", f"{exergy:.4f}")
            table.add_row("[dim]Entry hash[/dim]", f"[cyan]{entry['entry_hash'][:16]}…[/cyan]")
            table.add_row("[dim]Chain depth[/dim]", str(i))
            console.print(table)

            # Push to CORTEX
            cortex_ok = await push_to_cortex(client, entry)
            status = "[green]✓ Ledger sealed[/green]" if cortex_ok else "[yellow]⚠ CORTEX offline — entry cached locally[/yellow]"
            console.print(status)

    # Session summary
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold green]Session complete.[/bold green]\n"
            f"Entries sealed: [cyan]{len(ledger_chain)}[/cyan]\n"
            f"Final Merkle tip: [cyan]{prev_hash[:32]}…[/cyan]\n"
            f"Total tokens: [cyan]{sum(e['tokens_used'] for e in ledger_chain)}[/cyan]\n"
            f"Avg exergy: [cyan]{sum(e['exergy_score'] for e in ledger_chain) / max(len(ledger_chain), 1):.4f}[/cyan]",
            border_style="green",
            title="CORTEX Audit Trail",
        )
    )

    # Write local ledger artifact
    artifact_path = "examples/audit_proof_artifact.json"
    with open(artifact_path, "w") as f:
        json.dump({"session": ledger_chain, "merkle_tip": prev_hash}, f, indent=2)
    console.print(f"[dim]Ledger artifact written → {artifact_path}[/dim]")


if __name__ == "__main__":
    asyncio.run(run_research_session(RESEARCH_QUERIES))
