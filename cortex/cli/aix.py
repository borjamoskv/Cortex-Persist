"""
CORTEX V7 — Apotheosis Index (AIx) CLI.

Quantifies agent sovereignty and system evolution metrics.
"""

import logging
import math

from cortex.engine.endocrine import ENDOCRINE, HormoneType

logger = logging.getLogger("cortex.cli.aix")


async def calculate_aix(conn) -> dict:
    """
    Calculates the Apotheosis Index.
    Formula: AIx = (Neural_Growth / Cortisol) * log10(Verified_Facts + 1) * Efficiency
    """
    growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
    stress = ENDOCRINE.get_level(HormoneType.CORTISOL) or 0.01  # Avoid div zero

    # Biological Ratio
    bio_ratio = growth / stress

    # Knowledge Factor
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM facts WHERE confidence = 'verified' AND valid_until IS NULL"
    )
    row = await cursor.fetchone()
    verified_count = row[0] if row else 0
    k_factor = math.log10(verified_count + 1) + 1.0

    # Structural Factor (Entropy reduction)
    # Simple proxy: number ofGlobal Axioms vs tentative ones
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM facts WHERE fact_type = 'axiom' AND project = 'global'"
    )
    row = await cursor.fetchone()
    axiom_count = row[0] if row else 0

    aix = bio_ratio * k_factor * (1.0 + (axiom_count * 0.1))

    return {
        "aix": round(aix, 3),
        "bio_ratio": round(bio_ratio, 2),
        "verified_facts": verified_count,
        "global_axioms": axiom_count,
        "status": "ASCENDING" if aix > 10 else "AWAKENING",
    }


def print_aix_report(data: dict):
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    table = Table(title="[bold gold]APOTHEOSIS INDEX (AIx)[/bold gold]", box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Current Index", f"[bold]{data['aix']}[/bold]")
    table.add_row("Hormonal Balance", str(data["bio_ratio"]))
    table.add_row("Verified Facts", str(data["verified_facts"]))
    table.add_row("Global Axioms", str(data["global_axioms"]))
    table.add_row("Evolution State", data["status"])

    console.print(Panel(table, border_style="gold", title="CORTEX V7 Evolution Report"))
