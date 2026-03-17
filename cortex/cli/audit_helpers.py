"""Audit helper functions extracted from trust_cmds.py (Seal 8 LOC compliance)."""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.table import Table

from cortex.utils.landauer import audit_calcification

console = Console()


def audit_frontend() -> None:
    """Run Zero-Latency UI Axiom audit (CC < 5)."""
    from cortex.verification.frontend_oracle import FrontendOracle

    project_dir = os.getcwd()
    oracle = FrontendOracle()
    violations = []

    for root, _, files in os.walk(project_dir):
        if any(x in root for x in [".venv", ".git", "node_modules"]):
            continue
        for f in files:
            if f.endswith((".html", ".js", ".ts", ".jsx", ".tsx")):
                violations.extend(oracle.analyze_file(os.path.join(root, f)))

    if not violations:
        console.print(
            "[bold green]OK[/bold green] Zero-Latency Axiom (Ω₇) respected. All listeners CC < 5."
        )
        return

    console.print("[bold red]FAIL[/bold red] Axiom Violation: Frontend listeners exceeded CC 5.")
    for v in violations:
        console.print(
            f"  -> {v['file']} :: [yellow]{v['function']}[/yellow] (CC: {v['complexity']})"
        )
    sys.exit(1)


def audit_calcification_report(limit: int) -> None:
    """Run Landauer's Razor calcification audit."""
    from pathlib import Path

    cortex_root = Path(__file__).parent.parent
    results = audit_calcification(cortex_root, limit=limit)

    table = Table(title="💎 Landauer's Razor Audit (Omega-2)", expand=True, show_lines=True)
    table.add_column("File", style="cyan", ratio=3)
    table.add_column("LOC", justify="right", style="dim", ratio=1)
    table.add_column("Complexity", justify="right", style="dim", ratio=1)
    table.add_column("Score", style="bold yellow", justify="right", ratio=1)
    table.add_column("Status", justify="center", ratio=1)

    for r in results:
        status = (
            "[bold red]BONEY[/bold red]" if r["is_parasite"] else "[bold green]FLUID[/bold green]"
        )

        # Build subtree for parasite nodes
        if r["is_parasite"]:
            parasites = [n for n in r["nodes"] if n["is_parasite"]][:3]
            sub_lines = []
            for p in parasites:
                lines = p["end_line"] - p["start_line"] + 1
                sub_lines.append(
                    f"[dim]↳[/dim] [magenta]{p['name']}[/magenta] [dim]({p['type']})[/dim] "
                    f"→ [yellow]cx:{p['complexity']}[/yellow] "
                    f"[red]sc:{p['score']}[/red] [dim]({lines}L)[/dim]"
                )
            file_cell = f"{r['file']}\n" + "\n".join(sub_lines)
        else:
            file_cell = r["file"]

        table.add_row(file_cell, str(r["loc"]), str(r["complexity"]), f"{r['score']:.2f}", status)

    console.print(table)
    console.print(
        "  [dim]Threshold: Score > 50 (File) | Score > 30 (Node) indicates Calcification.[/dim]\n"
    )
