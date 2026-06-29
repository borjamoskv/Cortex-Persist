#!/usr/bin/env python3
"""
APEX Forge — Ontology Synthesizer & Normalizer
===============================================
Author: borjamoskv
Level:  C5-REAL

Parses APEX_CORE.md, detects gaps in ID sequences, synthesizes missing
entries, selects top-100/top-20/top-10 by priority, and emits:
  1. apex_registry_100.json  — canonical 100P + 100I + 20AP + 10RA
  2. APEX_CORE_FORGED.md     — regenerated markdown

Usage:
    python apex_forge.py [--source APEX_CORE.md] [--out-dir .]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ── Data Models ──────────────────────────────────────────────────────

@dataclass
class Primitive:
    id: str           # APEX-NNN
    opcode: str       # OP_XXX
    signature: str    # function signature
    complexity: str   # O(...)
    mutation: str     # physical mutation description
    execute: str      # execution semantics
    source: str = "parsed"  # parsed | synthesized

@dataclass
class Invariant:
    id: str           # OUROBOROS-NNN
    name: str         # INV_XXX
    logic: str        # causal logic
    risk: str         # P0 | P1 | P2
    source: str = "parsed"

@dataclass
class AntiPattern:
    id: str           # AP-NN
    name: str
    trigger: str
    penalty: str
    resolution: str
    source: str = "parsed"

@dataclass
class Redundancy:
    id: str           # RA-NN
    name: str
    mechanism: str
    overhead: str
    resilience: str
    source: str = "parsed"

@dataclass
class ForgeReport:
    primitives: list[Primitive] = field(default_factory=list)
    invariants: list[Invariant] = field(default_factory=list)
    antipatterns: list[AntiPattern] = field(default_factory=list)
    redundancies: list[Redundancy] = field(default_factory=list)
    gaps: dict = field(default_factory=dict)


# ── Parser ───────────────────────────────────────────────────────────

_PIPE_ROW = re.compile(r"^\|(.+)\|$")


def _split_row(line: str) -> list[str] | None:
    """Split a markdown table row into cells, stripping whitespace."""
    m = _PIPE_ROW.match(line.strip())
    if not m:
        return None
    cells = [c.strip() for c in m.group(1).split("|")]
    return cells


def _strip_bold(s: str) -> str:
    return s.replace("**", "").strip()


def _strip_backtick(s: str) -> str:
    return s.strip("`").strip()


def parse_apex_core(path: Path) -> ForgeReport:
    """Parse APEX_CORE.md and extract all entities."""
    report = ForgeReport()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    section = None  # current section being parsed

    for line in lines:
        stripped = line.strip()

        # Section detection
        if "100 PRIMITIVAS DE COLAPSO" in stripped or "PRIMITIVAS DE COLAPSO" in stripped:
            section = "primitives"
            continue
        elif "100 INVARIANTES" in stripped or "INVARIANTES TERMODINÁM" in stripped:
            section = "invariants"
            continue
        elif "ANTIPATRONES" in stripped:
            section = "antipatterns"
            continue
        elif "REDUNDANCIAS" in stripped:
            section = "redundancies"
            continue
        elif "ARSENAL ULTRATHINK" in stripped:
            section = None
            continue

        # Skip header/separator rows
        if stripped.startswith("|:") or stripped.startswith("| ID") or stripped.startswith("| --"):
            continue

        cells = _split_row(stripped)
        if cells is None:
            continue

        # Parse based on section
        if section == "primitives" and len(cells) >= 6:
            pid = _strip_bold(cells[0])
            if not pid.startswith("APEX-"):
                continue
            report.primitives.append(Primitive(
                id=pid,
                opcode=_strip_backtick(cells[1]),
                signature=_strip_backtick(cells[2]),
                complexity=_strip_backtick(cells[3]),
                mutation=cells[4],
                execute=cells[5],
            ))

        elif section == "invariants" and len(cells) >= 4:
            iid = _strip_bold(cells[0])
            if not iid.startswith("OUROBOROS-"):
                continue
            report.invariants.append(Invariant(
                id=iid,
                name=_strip_backtick(cells[1]),
                logic=_strip_backtick(cells[2]),
                risk=cells[3].strip(),
            ))

        elif section == "antipatterns" and len(cells) >= 5:
            aid = _strip_bold(cells[0])
            if not aid.startswith("AP-"):
                continue
            report.antipatterns.append(AntiPattern(
                id=aid,
                name=_strip_bold(cells[1]),
                trigger=_strip_backtick(cells[2]),
                penalty=_strip_backtick(cells[3]),
                resolution=cells[4],
            ))

        elif section == "redundancies" and len(cells) >= 5:
            rid = _strip_bold(cells[0])
            if not rid.startswith("RA-"):
                continue
            report.redundancies.append(Redundancy(
                id=rid,
                name=_strip_bold(cells[1]),
                mechanism=cells[2],
                overhead=_strip_backtick(cells[3]),
                resilience=cells[4],
            ))

    return report


# ── Gap Analysis ─────────────────────────────────────────────────────

def _extract_num(id_str: str, prefix: str) -> int:
    """Extract numeric part from ID like APEX-042 -> 42."""
    s = id_str.replace(prefix, "").lstrip("0") or "0"
    return int(s)


def find_gaps(
    items: list, prefix: str, target: int, start: int = 1
) -> dict:
    """Find missing IDs and excess entries."""
    present_nums = sorted(
        _extract_num(item.id, prefix) for item in items
    )
    present_set = set(present_nums)

    # Core range: 1..target
    expected = set(range(start, target + 1))
    missing = sorted(expected - present_set)
    overflow = sorted(n for n in present_nums if n > target)

    return {
        "total_parsed": len(items),
        "target": target,
        "missing_ids": [f"{prefix}{n:03d}" for n in missing],
        "overflow_ids": [f"{prefix}{n:03d}" for n in overflow],
        "missing_count": len(missing),
        "overflow_count": len(overflow),
    }


def find_gaps_ap(items: list, target: int = 20) -> dict:
    """Gap analysis for antipatterns (AP-NN format, may have AP-MCTS-NN)."""
    core_nums = []
    mcts_ids = []
    for item in items:
        if item.id.startswith("AP-MCTS"):
            mcts_ids.append(item.id)
        else:
            num = int(item.id.replace("AP-", "").lstrip("0") or "0")
            core_nums.append(num)

    present_set = set(core_nums)
    expected = set(range(1, target + 1))
    missing = sorted(expected - present_set)

    return {
        "total_parsed": len(items),
        "core_count": len(core_nums),
        "mcts_count": len(mcts_ids),
        "target": target,
        "missing_ids": [f"AP-{n:02d}" for n in missing],
        "overflow_ids": mcts_ids,
        "missing_count": len(missing),
    }


def find_gaps_ra(items: list, target: int = 10) -> dict:
    """Gap analysis for redundancies (RA-NN format, may have RA-MCTS-NN)."""
    core_nums = []
    mcts_ids = []
    for item in items:
        if item.id.startswith("RA-MCTS"):
            mcts_ids.append(item.id)
        else:
            num = int(item.id.replace("RA-", "").lstrip("0") or "0")
            core_nums.append(num)

    present_set = set(core_nums)
    expected = set(range(1, target + 1))
    missing = sorted(expected - present_set)

    return {
        "total_parsed": len(items),
        "core_count": len(core_nums),
        "mcts_count": len(mcts_ids),
        "target": target,
        "missing_ids": [f"RA-{n:02d}" for n in missing],
        "overflow_ids": mcts_ids,
        "missing_count": len(missing),
    }


# ── Synthesizer ──────────────────────────────────────────────────────

# Pre-defined synthesis templates for known gaps
_SYNTH_PRIMITIVES: dict[str, dict] = {
    "APEX-066": {
        "opcode": "OP_HEARTBEAT_PULSE",
        "signature": "ping_alive(agent_id)",
        "complexity": "O(1)",
        "mutation": "Red I/O. UDP heartbeat atómico sin handshake.",
        "execute": "Verificación de liveness en enjambre P2P.",
    },
    "APEX-098": {
        "opcode": "OP_CONTEXT_SNAPSHOT",
        "signature": "ctx_serialize(state)",
        "complexity": "O(S)",
        "mutation": "RAM → Disco. Serialización msgpack del contexto activo.",
        "execute": "Persistencia de sesión para handoff multi-agente.",
    },
    "APEX-099": {
        "opcode": "OP_CONTEXT_RESTORE",
        "signature": "ctx_deserialize(blob)",
        "complexity": "O(S)",
        "mutation": "Disco → RAM. Recarga atómica de estado previo.",
        "execute": "Restauración de punto de control cognitivo.",
    },
    "APEX-100": {
        "opcode": "OP_ENTROPY_ZERO",
        "signature": "entropy_audit(scope)",
        "complexity": "O(N)",
        "mutation": "CPU. Recorrido de nodos para medir Shannon/token.",
        "execute": "Aserción de que el sistema alcanzó equilibrio termodinámico.",
    },
}

_SYNTH_INVARIANTS: dict[str, dict] = {
    "OUROBOROS-021": {
        "name": "INV_HASH_MONOTONIC",
        "logic": "hash[i] = SHA256(hash[i-1] + payload[i]); ORDER(i) es estrictamente creciente",
        "risk": "P0",
    },
    "OUROBOROS-038": {
        "name": "INV_MEMORY_DECAY",
        "logic": "IF age(fact) > TTL AND access_count < 3 THEN evict(fact)",
        "risk": "P1",
    },
}


def synthesize_missing(report: ForgeReport) -> ForgeReport:
    """Fill gaps with synthesized entries."""
    # Primitives
    prim_gaps = find_gaps(report.primitives, "APEX-", 100)
    for mid in prim_gaps["missing_ids"]:
        if mid in _SYNTH_PRIMITIVES:
            t = _SYNTH_PRIMITIVES[mid]
            report.primitives.append(Primitive(
                id=mid, source="synthesized", **t,
            ))
        else:
            # Generic synthesis for unknown gaps
            num = _extract_num(mid, "APEX-")
            report.primitives.append(Primitive(
                id=mid,
                opcode=f"OP_SYNTH_{num:03d}",
                signature=f"synth_{num}(state)",
                complexity="O(1)",
                mutation=f"CPU. Primitiva sintetizada #{num}.",
                execute=f"Operación atómica de colapso #{num}.",
                source="synthesized",
            ))

    # Invariants
    inv_gaps = find_gaps(report.invariants, "OUROBOROS-", 100)
    for mid in inv_gaps["missing_ids"]:
        if mid in _SYNTH_INVARIANTS:
            t = _SYNTH_INVARIANTS[mid]
            report.invariants.append(Invariant(
                id=mid, source="synthesized", **t,
            ))
        else:
            num = _extract_num(mid, "OUROBOROS-")
            report.invariants.append(Invariant(
                id=mid,
                name=f"INV_SYNTH_{num:03d}",
                logic=f"ASSERT structural_invariant_{num} == TRUE",
                risk="P1",
                source="synthesized",
            ))

    # Antipatterns: keep core AP-01..AP-20, discard MCTS overflow
    # Redundancies: keep core RA-01..RA-10, discard MCTS overflow
    # (No gaps detected in AP or RA core ranges)

    return report


# ── Filter & Select ──────────────────────────────────────────────────

def select_canonical(report: ForgeReport) -> ForgeReport:
    """Select exactly 100P + 100I + 20AP + 10RA.

    Strategy:
    - Primitives: keep APEX-001..APEX-100, discard APEX-101+
    - Invariants: keep OUROBOROS-001..OUROBOROS-100, discard 101+
    - Antipatterns: keep AP-01..AP-20, discard AP-MCTS-*
    - Redundancies: keep RA-01..RA-10, discard RA-MCTS-*
    """
    canonical = ForgeReport()

    # Primitives: filter to 001-100
    for p in report.primitives:
        num = _extract_num(p.id, "APEX-")
        if 1 <= num <= 100:
            canonical.primitives.append(p)
    canonical.primitives.sort(key=lambda x: _extract_num(x.id, "APEX-"))

    # Invariants: filter to 001-100
    for inv in report.invariants:
        num = _extract_num(inv.id, "OUROBOROS-")
        if 1 <= num <= 100:
            canonical.invariants.append(inv)
    canonical.invariants.sort(key=lambda x: _extract_num(x.id, "OUROBOROS-"))

    # Antipatterns: core only
    for ap in report.antipatterns:
        if not ap.id.startswith("AP-MCTS"):
            canonical.antipatterns.append(ap)
    canonical.antipatterns.sort(
        key=lambda x: int(x.id.replace("AP-", "").lstrip("0") or "0")
    )

    # Redundancies: core only
    for ra in report.redundancies:
        if not ra.id.startswith("RA-MCTS"):
            canonical.redundancies.append(ra)
    canonical.redundancies.sort(
        key=lambda x: int(x.id.replace("RA-", "").lstrip("0") or "0")
    )

    return canonical


# ── Emitters ─────────────────────────────────────────────────────────

def emit_json(canonical: ForgeReport, out_dir: Path) -> Path:
    """Emit apex_registry_100.json."""
    data = {
        "meta": {
            "version": "1.0.0",
            "author": "borjamoskv",
            "level": "C5-REAL",
            "counts": {
                "primitives": len(canonical.primitives),
                "invariants": len(canonical.invariants),
                "antipatterns": len(canonical.antipatterns),
                "redundancies": len(canonical.redundancies),
            },
        },
        "primitives": [asdict(p) for p in canonical.primitives],
        "invariants": [asdict(i) for i in canonical.invariants],
        "antipatterns": [asdict(a) for a in canonical.antipatterns],
        "redundancies": [asdict(r) for r in canonical.redundancies],
    }
    out = out_dir / "apex_registry_100.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def emit_markdown(canonical: ForgeReport, out_dir: Path) -> Path:
    """Emit APEX_CORE_FORGED.md with exact counts."""
    lines: list[str] = []
    lines.append("# APEX_CORE: C5-REAL Sovereign Primitives & Invariants Registry")
    lines.append("")
    lines.append('> **"Cero Anergía es la Muerte."**')
    lines.append("> Documento canónico forjado por `apex_forge.py`.")
    lines.append(f"> **Counts:** {len(canonical.primitives)}P"
                 f" + {len(canonical.invariants)}I"
                 f" + {len(canonical.antipatterns)}AP"
                 f" + {len(canonical.redundancies)}RA")
    lines.append("")

    # Primitives
    lines.append("## 100 PRIMITIVAS DE COLAPSO (APEX CORE)")
    lines.append("")
    lines.append("| ID | Opcode | Firma | O(N) | Mutación C5 | Execute |")
    lines.append("|:---|:---|:---|:---:|:---|:---|")
    for p in canonical.primitives:
        src = " 🔧" if p.source == "synthesized" else ""
        lines.append(
            f"| **{p.id}**{src} | `{p.opcode}` | `{p.signature}` "
            f"| `{p.complexity}` | {p.mutation} | {p.execute} |"
        )
    lines.append("")

    # Invariants
    lines.append("## 100 INVARIANTES TERMODINÁMICAS (OUROBOROS LAWS)")
    lines.append("")
    lines.append("| ID | Invariante (Regla) | Lógica Causal | Riesgo |")
    lines.append("|:---|:---|:---|:---:|")
    for inv in canonical.invariants:
        src = " 🔧" if inv.source == "synthesized" else ""
        lines.append(
            f"| **{inv.id}**{src} | **{inv.name}** "
            f"| `{inv.logic}` | {inv.risk} |"
        )
    lines.append("")

    # Antipatterns
    lines.append("## 20 ANTIPATRONES ESTOCÁSTICOS")
    lines.append("")
    lines.append("| ID | Antipatrón | Trigger | Penalty | Resolution |")
    lines.append("|:---|:---|:---|:---|:---|")
    for ap in canonical.antipatterns:
        lines.append(
            f"| **{ap.id}** | **{ap.name}** "
            f"| `{ap.trigger}` | `{ap.penalty}` | {ap.resolution} |"
        )
    lines.append("")

    # Redundancies
    lines.append("## 10 REDUNDANCIAS ACTIVAS (MITIGACIÓN C5)")
    lines.append("")
    lines.append("| ID | Redundancia | Mecanismo | Overhead | Resiliencia |")
    lines.append("|:---|:---|:---|:---|:---|")
    for ra in canonical.redundancies:
        lines.append(
            f"| **{ra.id}** | **{ra.name}** "
            f"| {ra.mechanism} | `{ra.overhead}` | {ra.resilience} |"
        )
    lines.append("")

    out = out_dir / "APEX_CORE_FORGED.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="APEX Forge — Ontology Synthesizer & Normalizer"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).parent / "APEX_CORE.md",
        help="Path to APEX_CORE.md",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Output directory for generated files",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"[FATAL] Source not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Parse
    print("[PHASE-1] Parsing APEX_CORE.md...")
    report = parse_apex_core(args.source)
    print(f"  Primitives:   {len(report.primitives)}")
    print(f"  Invariants:   {len(report.invariants)}")
    print(f"  Antipatterns: {len(report.antipatterns)}")
    print(f"  Redundancies: {len(report.redundancies)}")

    # Phase 2: Gap Analysis
    print("\n[PHASE-2] Gap Analysis...")
    gaps = {
        "primitives": find_gaps(report.primitives, "APEX-", 100),
        "invariants": find_gaps(report.invariants, "OUROBOROS-", 100),
        "antipatterns": find_gaps_ap(report.antipatterns, 20),
        "redundancies": find_gaps_ra(report.redundancies, 10),
    }
    report.gaps = gaps
    for cat, g in gaps.items():
        print(f"  {cat}: {g['missing_count']} missing -> {g['missing_ids']}")

    # Phase 3: Synthesize
    print("\n[PHASE-3] Synthesizing missing entries...")
    report = synthesize_missing(report)
    print(f"  Primitives (post-synth):   {len(report.primitives)}")
    print(f"  Invariants (post-synth):   {len(report.invariants)}")

    # Phase 4: Select canonical set
    print("\n[PHASE-4] Selecting canonical 100+100+20+10...")
    canonical = select_canonical(report)
    print(f"  Primitives:   {len(canonical.primitives)}")
    print(f"  Invariants:   {len(canonical.invariants)}")
    print(f"  Antipatterns: {len(canonical.antipatterns)}")
    print(f"  Redundancies: {len(canonical.redundancies)}")

    # Validation
    assert len(canonical.primitives) == 100, (
        f"Expected 100 primitives, got {len(canonical.primitives)}"
    )
    assert len(canonical.invariants) == 100, (
        f"Expected 100 invariants, got {len(canonical.invariants)}"
    )
    assert len(canonical.antipatterns) == 20, (
        f"Expected 20 antipatterns, got {len(canonical.antipatterns)}"
    )
    assert len(canonical.redundancies) == 10, (
        f"Expected 10 redundancies, got {len(canonical.redundancies)}"
    )

    # Phase 5: Emit
    print("\n[PHASE-5] Emitting outputs...")
    json_path = emit_json(canonical, args.out_dir)
    md_path = emit_markdown(canonical, args.out_dir)
    print(f"  JSON:     {json_path}")
    print(f"  Markdown: {md_path}")

    # Summary
    synth_p = sum(1 for p in canonical.primitives if p.source == "synthesized")
    synth_i = sum(1 for i in canonical.invariants if i.source == "synthesized")
    print(f"\n[DONE] Synthesized: {synth_p}P + {synth_i}I")
    print(f"       Discarded overflow: "
          f"{gaps['primitives']['overflow_count']}P "
          f"+ {gaps['invariants']['overflow_count']}I "
          f"+ {gaps['antipatterns']['mcts_count']}AP "
          f"+ {gaps['redundancies']['mcts_count']}RA")


if __name__ == "__main__":
    main()
