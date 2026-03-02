#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate docs/axiom-registry.md from the canonical Python registry.

Usage:
    python -m cortex.axioms.generate_docs

This ensures the markdown doc is always in sync with the code.
"""

from __future__ import annotations

from pathlib import Path

from cortex.axioms.registry import (
    AXIOM_REGISTRY,
    AxiomCategory,
    by_category,
    enforced,
)
from cortex.axioms.ttl import FACT_TTL, ttl_days


def _header() -> str:
    return """\
# Axiom Registry — Canonical Source of Truth

> *One numbering. One taxonomy. One source.*
> **Auto-generated from `cortex/axioms/registry.py` — do not edit manually.**

### Axiom Zero (α₀)

> *"Every axiom without a CI gate is, at best, an aspiration; at worst, a hallucination with persistence."*

---

## Taxonomy

| Layer | IDs | Nature | Enforcement | Count |
|:---|:---|:---|:---|:---:|
| 🔴 **Constitutional** | AX-001 – AX-003 | Defines what the agent *is* | Identity — not CI-enforceable | {const} |
| 🔵 **Operational** | AX-010 – AX-019 | Defines how the agent *operates* | CI gates, middleware, lint | {oper} |
| 🟡 **Aspirational** | AX-020 – AX-028 | Guides decisions and culture | Convention, design review | {aspir} |

**Precedence:** Constitutional > Operational > Aspirational.

**Axiom Cap:** ≤ 25 — No new axioms until enforcement coverage exceeds 60%.

---
""".format(
        const=len(by_category(AxiomCategory.CONSTITUTIONAL)),
        oper=len(by_category(AxiomCategory.OPERATIONAL)),
        aspir=len(by_category(AxiomCategory.ASPIRATIONAL)),
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
            lines.append(f"| **{ax.id}** | {ax.name} | {ax.mandate[:80]}{'…' if len(ax.mandate) > 80 else ''} | {gate} |\n")
    else:
        lines.append(
            "| ID | Name | Mandate |\n"
            "|:---|:---|:---|\n"
        )
        for ax in axioms:
            lines.append(f"| **{ax.id}** | {ax.name} | {ax.mandate[:100]}{'…' if len(ax.mandate) > 100 else ''} |\n")

    lines.append("\n---\n\n")
    return "".join(lines)


def _ttl_section() -> str:
    lines = [
        "## Fact TTL Policy (AX-019)\n\n",
        "> *Persist aggressively. Decay intelligently.*\n\n",
        "| Fact Type | TTL | Days |\n",
        "|:---|:---|:---:|\n",
    ]
    for fact_type, ttl in FACT_TTL.items():
        days = ttl_days(fact_type)
        ttl_str = "∞ (immortal)" if days is None else f"{days} days"
        lines.append(f"| `{fact_type}` | {ttl_str} | {'∞' if days is None else days} |\n")

    lines.append("\n---\n\n")
    return "".join(lines)


def _metrics() -> str:
    total = len(AXIOM_REGISTRY)
    enf = len(enforced())
    pct = round(enf / total * 100) if total else 0
    return f"""\
## Metrics

```
Total Axioms           : {total}
CI-Enforced            : {enf} ({pct}%)
Axiom Cap              : 25
Inflation Rate Target  : 0 (no new axioms without compaction)
```

---

*Auto-generated from `cortex/axioms/registry.py` — {__import__('datetime').date.today().isoformat()}*
"""


def generate() -> str:
    """Generate the full axiom registry markdown."""
    parts = [
        _header(),
        _section("Constitutional", "🔴", AxiomCategory.CONSTITUTIONAL),
        _section("Operational — CI-Enforced", "🔵", AxiomCategory.OPERATIONAL),
        _section("Aspirational — Vision", "🟡", AxiomCategory.ASPIRATIONAL),
        _ttl_section(),
        _metrics(),
    ]
    return "\n".join(parts)


def main() -> None:
    """Write the registry doc to docs/axiom-registry.md."""
    doc = generate()
    out = Path(__file__).resolve().parents[2] / "docs" / "axiom-registry.md"
    out.write_text(doc)
    print(f"✅ Generated {out} ({len(doc)} bytes, {doc.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
