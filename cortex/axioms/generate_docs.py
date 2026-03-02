#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate docs/axiom-registry.md from the canonical Python registry.

Usage:
    python -m cortex.axioms.generate_docs

This ensures the markdown doc is always in sync with the code.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from cortex.axioms.registry import (
    AXIOM_REGISTRY,
    AxiomCategory,
    by_category,
    enforced,
)
from cortex.axioms.ttl import FACT_TTL, ttl_days


def _header() -> str:
    const = len(by_category(AxiomCategory.CONSTITUTIONAL))
    oper = len(by_category(AxiomCategory.OPERATIONAL))
    aspir = len(by_category(AxiomCategory.ASPIRATIONAL))
    return (
        "# Axiom Registry — Canonical Source of Truth\n\n"
        "> *One numbering. One taxonomy. One source.*\n"
        "> **Auto-generated from `cortex/axioms/registry.py`"
        " — do not edit manually.**\n\n"
        "### Axiom Zero (α₀)\n\n"
        "> *\"Every axiom without a CI gate is, at best, "
        "an aspiration; at worst, a hallucination "
        "with persistence.\"*\n\n---\n\n"
        "## Taxonomy\n\n"
        "| Layer | IDs | Nature | Count |\n"
        "|:---|:---|:---|:---:|\n"
        f"| 🔴 **Constitutional** | AX-001 – AX-003 | Identity | {const} |\n"
        f"| 🔵 **Operational** | AX-010 – AX-019 | CI-Enforced | {oper} |\n"
        f"| 🟡 **Aspirational** | AX-020 – AX-028 | Vision | {aspir} |\n\n"
        "**Precedence:** Constitutional > Operational > Aspirational.\n\n"
        "---\n\n"
    )


def _section(title: str, emoji: str, category: AxiomCategory) -> str:
    axioms = by_category(category)
    lines = [f"## {emoji} {title} ({len(axioms)})\n"]

    if category == AxiomCategory.OPERATIONAL:
        lines.append(
            "| ID | Name | Mandate | CI Gate |\n"
            "|:---|:---|:---|:---|\n"
        )
        for ax in axioms:
            gate = ax.ci_gate or "—"
            mandate = ax.mandate[:80]
            ellip = "…" if len(ax.mandate) > 80 else ""
            lines.append(
                f"| **{ax.id}** | {ax.name} "
                f"| {mandate}{ellip} | {gate} |\n"
            )
    else:
        lines.append(
            "| ID | Name | Mandate |\n"
            "|:---|:---|:---|\n"
        )
        for ax in axioms:
            mandate = ax.mandate[:100]
            ellip = "…" if len(ax.mandate) > 100 else ""
            lines.append(
                f"| **{ax.id}** | {ax.name} "
                f"| {mandate}{ellip} |\n"
            )

    lines.append("\n---\n\n")
    return "".join(lines)


def _ttl_section() -> str:
    lines = [
        "## Fact TTL Policy (AX-019)\n\n",
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
        "Axiom Cap              : 25\n"
        "Inflation Rate Target  : 0\n"
        "```\n\n---\n\n"
        "*Auto-generated from `cortex/axioms/registry.py`"
        f" — {today}*\n"
    )


def generate() -> str:
    """Generate the full axiom registry markdown."""
    parts = [
        _header(),
        _section("Constitutional", "🔴", AxiomCategory.CONSTITUTIONAL),
        _section(
            "Operational — CI-Enforced", "🔵",
            AxiomCategory.OPERATIONAL,
        ),
        _section(
            "Aspirational — Vision", "🟡",
            AxiomCategory.ASPIRATIONAL,
        ),
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
