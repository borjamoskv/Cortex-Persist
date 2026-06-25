#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
# SPDX-License-Identifier: Apache-2.0
"""Generate docs/axiom-registry.md from the canonical Python registry.

Usage:
    python -m cortex.extensions.axioms.generate_docs

This ensures the markdown doc is always in sync with the code.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from legacy_research.extensions.axioms.registry import (
    AXIOM_REGISTRY,
    AxiomCategory,
    by_category,
    enforced,
)
from legacy_research.extensions.axioms.ttl import FACT_TTL, ttl_days


def _header() -> str:
    total = len(AXIOM_REGISTRY)
    return (
        "# Axiom Registry - Canonical Source of Truth\n\n"
        "> *Los 7 Axiomas Soberanos. One numbering. One taxonomy. One source.*\n"
        "> **Auto-generated from `cortex/extensions/axioms/registry.py`"
        " - do not edit manually.**\n\n"
        "### Invarianza Total\n\n"
        '> *"CORTEX no aumenta la inteligencia del modelo fundacional; '
        'restringe rígidamente su libertad estructural para contaminar la arquitectura."*\n\n---\n\n'
        "## Taxonomy\n\n"
        "| Layer | IDs | Nature | Count |\n"
        "|:---|:---|:---|:---:|\n"
        f"| 🌌 **Sovereign** | AX-I – AX-VII | Architectonic Core | {total} |\n\n"
        "---\n\n"
    )


def _section(title: str, emoji: str, category: AxiomCategory) -> str:
    axioms = by_category(category)
    lines = [f"## {emoji} {title} ({len(axioms)})\n"]

    lines.append("| ID | Name | Mandate | CI Gate/Enforcement |\n|:---|:---|:---|:---|\n")
    for ax in axioms:
        gate = ax.ci_gate or "-"
        mandate = ax.mandate.replace("\n", " ")
        lines.append(f"| **{ax.id}** | {ax.name} | {mandate} | {gate} |\n")

    lines.append("\n---\n\n")
    return "".join(lines)


def _ttl_section() -> str:
    lines = [
        "## Fact TTL Policy\n\n",
        "> *Persist aggressively. Decay intelligently.*\n\n",
        "| Fact Type | TTL | Days |\n",
        "|:---|:---|:---:|\n",
    ]
    for fact_type in FACT_TTL:
        days = ttl_days(fact_type)
        ttl_str = "∞ (immortal)" if days is None else f"{days} days"
        d_col = "∞" if days is None else str(days)
        lines.append(f"| `{fact_type}` | {ttl_str} | {d_col} |\n")

    lines.append("\n---\n\n")
    return "".join(lines)


def _metrics() -> str:
    total = len(AXIOM_REGISTRY)
    enf = len(enforced())
    pct = round(enf / total * 100) if total else 0
    today = datetime.date.today().isoformat()
    return (
        "## Metrics\n\n"
        "```\n"
        f"Total Axioms           : {total}\n"
        f"CI-Enforced            : {enf} ({pct}%)\n"
        "Axiom Cap              : 7\n"
        "Inflation Rate Target  : 0\n"
        "```\n\n---\n\n"
        "*Auto-generated from `cortex/extensions/axioms/registry.py`"
        f" - {today}*\n"
    )


def generate() -> str:
    """Generate the full axiom registry markdown."""
    parts = [
        _header(),
        _section("The 7 Sovereign Axioms", "⚙️", AxiomCategory.SOVEREIGN),
        _ttl_section(),
        _metrics(),
    ]
    return "\n".join(parts)


def main() -> None:
    """Write the registry doc to docs/axiom-registry.md."""
    doc = generate()
    out = Path(__file__).resolve().parents[2] / "docs" / "axiom-registry.md"
    out.write_text(doc)
    lines = doc.count(chr(10))
    print(f"✅ Generated {out} ({len(doc)} bytes, {lines} lines)")


if __name__ == "__main__":
    main()
